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
            status="pending_admin_approval"
        )
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
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
        
    order.status = "approved_waiting_for_mt5_id"
    await db.commit()
    return {"status": "success", "message": f"Order {order_id} approved", "telegram_id": user.telegram_id, "mt5_id": order.mt5_id or ""}

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
    from sqlalchemy import text
    # Reset sqlite_sequence if table is empty
    count_res = await db.execute(text("SELECT COUNT(*) FROM orders"))
    if count_res.scalar() == 0:
        await db.execute(text("DELETE FROM sqlite_sequence WHERE name='orders'"))
    else:
        max_res = await db.execute(text("SELECT MAX(id) FROM orders"))
        max_id = max_res.scalar() or 0
        await db.execute(text(f"UPDATE sqlite_sequence SET seq = {max_id} WHERE name='orders'"))
    await db.commit()

    return {"status": "success", "message": "Order deleted"}
