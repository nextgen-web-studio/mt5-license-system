from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models import Order, Product, License, CompileJob, VpsOrder, AdminNotification
from app.schemas import OrderCreate, OrderResponse, OrderFulfillmentRequest

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(order: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        if order.order_type == "EA" and order.mt5_id:
            existing_license = await db.execute(select(License).filter(
                License.mt5_id == order.mt5_id,
                License.status == "active"
            ))
            if existing_license.scalars().first():
                raise HTTPException(status_code=400, detail="This MT5 ID already has an active license.")
                
        db_order = Order(
            user_id=order.user_id,
            product_id=order.product_id,
            order_type=order.order_type,
            mt5_id=order.mt5_id,
            status="pending"
        )
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        return db_order
    except Exception as e:
        import traceback
        error_msg = f"DB Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}", response_model=List[OrderResponse])
async def get_user_orders(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.user_id == user_id))
    orders = result.scalars().all()
    return orders

@router.get("/", response_model=List[OrderResponse])
async def get_all_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return orders

@router.post("/{order_id}/start-fulfillment")
async def start_fulfillment(order_id: int, req: OrderFulfillmentRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status != "paid":
        raise HTTPException(status_code=400, detail=f"Cannot fulfill order in {order.status} state")

    result = await db.execute(select(Product).filter(Product.id == order.product_id))
    product = result.scalar_one_or_none()

    if order.order_type == "EA":
        if not req.mt5_id:
            raise HTTPException(status_code=400, detail="mt5_id is required for EA fulfillment")
            
        # Check for MT5 ID uniqueness
        existing_license = await db.execute(select(License).filter(License.mt5_id == req.mt5_id))
        if existing_license.scalars().first():
            raise HTTPException(status_code=400, detail="This MT5 ID is already in use by a license.")
            
        expiry_date = datetime.utcnow() + timedelta(days=product.duration * 30)
        
        db_license = License(
            order_id=order.id,
            user_id=order.user_id,
            mt5_id=req.mt5_id,
            expiry_date=expiry_date,
            status="active"
        )
        db.add(db_license)
        await db.commit()
        await db.refresh(db_license)
        
        compile_job = CompileJob(
            license_id=db_license.id,
            status="pending"
        )
        db.add(compile_job)
        
        order.status = "compiling"
        await db.commit()
        
        return {"status": "success", "message": "License created and compile job queued", "license_id": db_license.id}
        
    elif order.order_type == "VPS":
        vps_order = VpsOrder(
            order_id=order.id,
            user_id=order.user_id,
            duration=product.duration,
            status="pending"
        )
        db.add(vps_order)
        
        notification = AdminNotification(
            title="New VPS Order",
            message=f"Order #{order.id} needs VPS provisioning for {product.duration} months.",
            status="unread"
        )
        db.add(notification)
        await db.commit()
        
        # Notify Admin via Telegram
        import os
        import httpx
        admin_chat_id = os.getenv("ADMIN_TELEGRAM_ID")
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if admin_chat_id and bot_token:
            async with httpx.AsyncClient(verify=False) as client:
                try:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": admin_chat_id,
                            "text": f"🚨 *New VPS Order!*\n\nOrder #{order.id} needs VPS provisioning for {product.duration} months.",
                            "parse_mode": "Markdown"
                        }
                    )
                except Exception as e:
                    print(f"Failed to send admin notification: {e}")
        
        return {"status": "success", "message": "VPS order created and admin notified"}

@router.get("/{order_id}/mock-pay")
async def mock_pay(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        order.status = "paid"
        await db.commit()
    return {"status": "ok"}
