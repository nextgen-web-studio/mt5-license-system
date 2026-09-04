from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta
import dateutil.relativedelta

from app.db.database import get_db
from app.models import Order, Product, License, CompileJob, VpsOrder, AdminNotification
from app.schemas import OrderCreate, OrderResponse, OrderFulfillmentRequest
from app.core.azure_vm import start_azure_vm_if_needed
from pydantic import BaseModel

class OrderMt5Update(BaseModel):
    mt5_id: str

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(order: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        if order.mt5_id:
            from sqlalchemy import and_
            from app.models import License
            dup_stmt = select(License).filter(
                and_(
                    License.mt5_id == order.mt5_id,
                    License.status.in_(["active", "generating", "pending", "compiling"])
                )
            )
            dup_res = await db.execute(dup_stmt)
            if dup_res.first():
                raise HTTPException(status_code=400, detail="This MT5 ID is already registered to another active license in the system.")
                
        db_order = Order(
            user_id=order.user_id,
            product_id=order.product_id,
            order_type=order.order_type,
            mt5_id=order.mt5_id,
            vps_id=order.vps_id,
            status="pending_admin_approval"
        )
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        
        if order.order_type == "VPS" and not order.vps_id:
            from app.models import VpsOrder, Product
            prod_res = await db.execute(select(Product).filter(Product.id == order.product_id))
            db_product = prod_res.scalar_one_or_none()
            prod_duration = db_product.duration if db_product and db_product.duration else 1
            
            vps_ord = VpsOrder(
                order_id=db_order.id,
                user_id=order.user_id,
                duration=prod_duration,
                status="pending"
            )
            db.add(vps_ord)
            await db.commit()
            
        return db_order
    except Exception as e:
        import logging
        logging.error(f"DB Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

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

@router.get("/telegram/{telegram_id}")
async def get_telegram_orders(telegram_id: str, db: AsyncSession = Depends(get_db)):
    from app.models import User, Product
    # Fetch orders belonging to this telegram_id
    query = (
        select(Order, Product)
        .join(User, Order.user_id == User.id)
        .join(Product, Order.product_id == Product.id)
        .filter(User.telegram_id == telegram_id)
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    orders = []
    for order, product in rows:
        orders.append({
            "id": order.id,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "product_name": product.name,
            "price": product.price
        })
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/{order_id}/approve")
async def approve_order(order_id: int, db: AsyncSession = Depends(get_db)):
    from app.models import User
    result = await db.execute(select(Order, User).join(User, Order.user_id == User.id).filter(Order.id == order_id))
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order, user = row
        
    if order.status != "pending_admin_approval":
        raise HTTPException(status_code=400, detail=f"Cannot approve order in {order.status} state")
        
    is_renewal = False
    new_expiry_str = ""
    if order.order_type == "VPS" and order.vps_id:
        from app.models import VpsOrder, Product
        v_res = await db.execute(select(VpsOrder).filter(VpsOrder.id == order.vps_id))
        v_order = v_res.scalar_one_or_none()
        p_res = await db.execute(select(Product).filter(Product.id == order.product_id))
        p_prod = p_res.scalar_one_or_none()
        if v_order and p_prod:
            from datetime import datetime, timezone
            from dateutil.relativedelta import relativedelta
            now = datetime.now(timezone.utc)
            if not v_order.expiry_date or v_order.expiry_date.replace(tzinfo=timezone.utc) < now:
                v_order.expiry_date = now + relativedelta(months=p_prod.duration)
            else:
                v_order.expiry_date = v_order.expiry_date.replace(tzinfo=timezone.utc) + relativedelta(months=p_prod.duration)
            new_expiry_str = v_order.expiry_date.strftime('%d %B %Y, %H:%M')
            is_renewal = True
            v_order.status = "delivered"
            
        order.status = "delivered"
    else:
        if order.mt5_id:
            order.status = "approved"
        else:
            order.status = "approved_waiting_for_mt5_id"
        
    await db.commit()
    
    # Notify bot to clear admin buttons
    import os, httpx, asyncio
    bot_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-k6h3.onrender.com")
    bot_webhook_url = bot_webhook_url.replace("/internal/delivery", "").replace("/internal/compile-started", "").replace("/internal/order-approved", "").replace("/bot", "").rstrip("/")
    bot_webhook_url += "/internal/order-approved" 
    try:
        async def trigger_clear_buttons():
            async with httpx.AsyncClient(verify=False) as client:
                await client.post(bot_webhook_url, json={"order_id": order_id})
        asyncio.create_task(trigger_clear_buttons())
    except Exception as e:
        pass
    
    if order.order_type in ["EA", "EA_RENEWAL"] and user.telegram_id and order.mt5_id:
        import os
        import httpx
        import asyncio
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            msg = f"✅ *YOUR ORDER HAS BEEN APPROVED*\n\nYour EA order (ORD-{order_id}) has been approved.\n\nYour EA is being prepared and will be delivered to you shortly."
            async def send_tg_ea():
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                    )
            asyncio.create_task(send_tg_ea())
    
    # Send Telegram notification automatically if it's a VPS order
    if order.order_type == "VPS" and user.telegram_id:
        import os
        import httpx
        import asyncio
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            if is_renewal:
                msg = f"✅ *YOUR VPS HAS BEEN RENEWED!*\n\nYour VPS renewal (ORD-{order_id}) has been successfully approved.\nYour server expiry date has been extended to: **{new_expiry_str}**."
            else:
                msg = f"✅ *YOUR VPS ORDER HAS BEEN APPROVED*\n\nYour VPS order (ORD-{order_id}) has been approved.\n\nThe admin will contact you shortly to provide your VPS credentials."
            
            async def send_tg():
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                    )
            asyncio.create_task(send_tg())
            
    return {"status": "success", "message": f"Order {order_id} approved", "telegram_id": user.telegram_id, "mt5_id": order.mt5_id or "", "order_type": order.order_type, "is_renewal": is_renewal, "new_expiry": new_expiry_str}

@router.put("/{order_id}/mt5")
async def update_order_mt5(order_id: int, payload: OrderMt5Update, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order.mt5_id = payload.mt5_id
    await db.commit()
    return {"status": "success", "message": "MT5 ID saved successfully"}

@router.post("/{order_id}/reject")
async def reject_order(order_id: int, db: AsyncSession = Depends(get_db)):
    from app.models import User
    result = await db.execute(select(Order, User).join(User, Order.user_id == User.id).filter(Order.id == order_id))
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order, user = row
        
    if order.status != "pending_admin_approval":
        raise HTTPException(status_code=400, detail=f"Cannot reject order in {order.status} state")
        
    order.status = "rejected"
    await db.commit()
    return {"status": "success", "message": f"Order {order_id} rejected", "telegram_id": user.telegram_id}

@router.delete("/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    from app.models import Payment, InstallmentPayment, License, VpsOrder, CompileJob, TrialActivation, TrialClaim, LicenseMt5History, BrokerChangeRequest
    await db.execute(Payment.__table__.delete().where(Payment.order_id == order_id))
    await db.execute(InstallmentPayment.__table__.delete().where(InstallmentPayment.order_id == order_id))
    await db.execute(VpsOrder.__table__.delete().where(VpsOrder.order_id == order_id))
    
    lic_res = await db.execute(select(License).filter(License.order_id == order_id))
    lics = lic_res.scalars().all()
    for l in lics:
        await db.execute(CompileJob.__table__.delete().where(CompileJob.license_id == l.id))
        await db.execute(TrialActivation.__table__.delete().where(TrialActivation.license_id == l.id))
        await db.execute(TrialClaim.__table__.delete().where(TrialClaim.license_id == l.id))
        await db.execute(LicenseMt5History.__table__.delete().where(LicenseMt5History.license_id == l.id))
        await db.execute(BrokerChangeRequest.__table__.delete().where(BrokerChangeRequest.license_id == l.id))
        await db.delete(l)

    await db.delete(order)
    await db.commit()


    return {"status": "success", "message": "Order deleted"}
