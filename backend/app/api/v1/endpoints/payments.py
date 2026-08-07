from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
import os
import httpx
from fastapi import Request
from app.models import Payment, Order, User
from app.schemas import PaymentCreate, PaymentResponse
from app.services.payment import create_payment_link, verify_webhook_signature

router = APIRouter()

@router.post("/create-payment-link")
async def create_link(payment_in: PaymentCreate, db: AsyncSession = Depends(get_db)):
    # Verify order exists
    result = await db.execute(select(Order).filter(Order.id == payment_in.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    try:
        # Create payment link in Razorpay
        reference_id = f"order_{order.id}"
        rzp_link = create_payment_link(amount=payment_in.amount, reference_id=reference_id)
        
        # Save payment record in DB
        db_payment = Payment(
            order_id=order.id,
            razorpay_order_id=rzp_link["id"], # Store payment link ID here for now
            amount=payment_in.amount,
            status="created"
        )
        db.add(db_payment)
        await db.commit()
        await db.refresh(db_payment)
        
        return {"payment_link_url": rzp_link["short_url"], "id": rzp_link["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "my_test_secret")
    
    # if not verify_webhook_signature(body.decode(), signature, secret):
    #     raise HTTPException(status_code=400, detail="Invalid signature")
        
    payload = await request.json()
    event = payload.get("event")
    
    if event == "payment_link.paid":
        p_link = payload["payload"]["payment_link"]["entity"]
        reference_id = p_link.get("reference_id") # e.g. "order_1"
        if not reference_id or not reference_id.startswith("order_"):
            return {"status": "ignored"}
            
        order_id = int(reference_id.split("_")[1])
        
        # Mark order as paid
        result = await db.execute(select(Order).filter(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order and order.status != "paid":
            order.status = "paid"
            await db.commit()
            
            # Get user telegram_id
            user_result = await db.execute(select(User).filter(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            
            from app.models import Product
            product_result = await db.execute(select(Product).filter(Product.id == order.product_id))
            product = product_result.scalar_one_or_none()
            
            if user and product:
                # Notify via Telegram
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                if bot_token:
                    if product.type == "EA":
                        msg = "✅ *Payment Received!*\n\nPlease enter your **MT5 ID** to generate your license:"
                    else:
                        msg = "✅ *Payment Received!*\n\n⏳ *Creating VPS...*\n\nAdmin has been notified and will provision your VPS shortly."
                        
                    async with httpx.AsyncClient(verify=False) as client:
                        await client.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                        )
                        
                    if product.type != "EA":
                        # Hit fulfillment without MT5 ID
                        async with httpx.AsyncClient(verify=False) as client:
                            await client.post(f"http://localhost:8000/api/v1/orders/{order.id}/start-fulfillment", json={"mt5_id": None})
                        
    return {"status": "ok"}
