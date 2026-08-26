from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import datetime
from dateutil.relativedelta import relativedelta

from app.db.database import get_db
from app.models import Order, InstallmentPayment, License, Product, User, CompileJob
from app.schemas.installments import InstallmentCreate, InstallmentCustomerResponse, InstallmentPaymentRecord, InstallmentPayRequest
from app.core.local_compiler import local_wine_compiler

router = APIRouter()

@router.post("/create")
async def create_installment_arrangement(payload: InstallmentCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == payload.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.installment_enabled = True
    order.installment_total_amount = payload.total_amount
    order.installment_amount = payload.installment_amount
    order.installment_count = payload.installment_count
    order.installments_paid = 1
    order.amount_paid = payload.first_payment_amount
    order.amount_remaining = payload.total_amount - payload.first_payment_amount
    order.license_period_days = payload.license_period_days
    from datetime import timezone
    current_time = datetime.datetime.now(timezone.utc)
    order.next_due_date = current_time + relativedelta(days=payload.license_period_days)
    payment = InstallmentPayment(order_id=order.id, amount=payload.first_payment_amount, payment_number=1, status="confirmed")
    db.add(payment)
    lic_res = await db.execute(select(License).filter(License.order_id == order.id))
    lic = lic_res.scalar_one_or_none()
    expiry = order.next_due_date
    if not lic:
        if not order.mt5_id:
            raise HTTPException(status_code=400, detail="Order is missing MT5 ID")
        import uuid
        lic = License(order_id=order.id, user_id=order.user_id, mt5_id=order.mt5_id, expiry_date=expiry, status="generating", license_type="paid", license_uuid=str(uuid.uuid4()))
        db.add(lic)
        await db.flush()
    else:
        lic.expiry_date = expiry
        lic.status = "generating"
    job = CompileJob(license_id=lic.id, status="pending")
    db.add(job)
    order.status = "compiling"
    await db.commit()
    background_tasks.add_task(local_wine_compiler, job.id)
    return {"status": "success", "message": "Installment arrangement created and first payment recorded"}

@router.post("/pay")
async def pay_installment(payload: InstallmentPayRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == payload.order_id))
    order = result.scalar_one_or_none()
    if not order or not order.installment_enabled:
        raise HTTPException(status_code=404, detail="Order not found or not installment enabled")
    if order.installment_status == "completed":
        raise HTTPException(status_code=400, detail="All installments already paid.")
    if order.installments_paid >= order.installment_count:
        raise HTTPException(status_code=400, detail=f"All {order.installment_count} installments already recorded.")
    order.installments_paid += 1
    order.amount_paid += payload.amount
    order.amount_remaining = max(0, order.installment_total_amount - order.amount_paid)
    from datetime import timezone
    current_time = datetime.datetime.now(timezone.utc)
    lic_res = await db.execute(select(License).filter(License.order_id == order.id))
    lic = lic_res.scalar_one_or_none()
    # Final = all installments paid OR user paid full remaining amount early
    is_final = order.installments_paid >= order.installment_count or order.amount_remaining <= 0
    if is_final:
        order.installment_status = "completed"
        order.next_due_date = None
        order.amount_remaining = 0
        order.installments_paid = order.installment_count
    else:
        # Extend 30 days from CURRENT EXPIRY (not today) so early payers never lose days
        if lic and lic.expiry_date:
            current_expiry = lic.expiry_date
            if current_expiry.tzinfo is None:
                current_expiry = current_expiry.replace(tzinfo=timezone.utc)
            base_date = max(current_expiry, current_time)
        else:
            base_date = current_time
        order.next_due_date = base_date + relativedelta(days=order.license_period_days)
    payment = InstallmentPayment(order_id=order.id, amount=payload.amount, payment_number=order.installments_paid, status="confirmed")
    db.add(payment)
    job = None
    if lic:
        if is_final:
            lic.expiry_date = None
            lic.license_type = "paid"
        else:
            lic.expiry_date = order.next_due_date
        lic.status = "generating"
        job = CompileJob(license_id=lic.id, status="pending")
        db.add(job)
    await db.commit()
    if lic and job:
        background_tasks.add_task(local_wine_compiler, job.id)
    return {
        "status": "success",
        "message": "Payment recorded. Lifetime EA being compiled!" if is_final else f"Payment recorded. License extended to {order.next_due_date.strftime('%d %b %Y') if order.next_due_date else 'N/A'}",
        "is_final": is_final,
        "license_id": lic.id if lic else None
    }

@router.post("/admin/settle/{order_id}")
async def full_settle_installment(order_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Admin marks installment as fully settled. Customer gets Lifetime EA immediately."""
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order or not order.installment_enabled:
        raise HTTPException(status_code=404, detail="Installment arrangement not found")
    if order.installment_status == "completed":
        raise HTTPException(status_code=400, detail="Installment is already completed.")
    order.installment_status = "completed"
    order.installments_paid = order.installment_count
    order.amount_paid = order.installment_total_amount
    order.amount_remaining = 0
    order.next_due_date = None
    lic_res = await db.execute(select(License).filter(License.order_id == order.id))
    lic = lic_res.scalar_one_or_none()
    job = None
    if lic:
        lic.expiry_date = None
        lic.license_type = "paid"
        lic.status = "generating"
        job = CompileJob(license_id=lic.id, status="pending")
        db.add(job)
    await db.commit()
    if lic and job:
        background_tasks.add_task(local_wine_compiler, job.id)
    user_res = await db.execute(select(User).filter(User.id == order.user_id))
    user = user_res.scalar_one_or_none()
    return {
        "status": "success",
        "message": "Full settlement recorded. Lifetime EA being compiled!",
        "telegram_id": user.telegram_id if user else None,
        "license_id": lic.id if lic else None
    }

@router.get("/customer/{telegram_id}", response_model=InstallmentCustomerResponse)
async def get_customer_installment(telegram_id: str, db: AsyncSession = Depends(get_db)):
    u_res = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    user = u_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    o_res = await db.execute(select(Order).filter(Order.user_id == user.id, Order.installment_enabled == True).order_by(Order.id.desc()))
    order = o_res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="No active installment arrangement found")
    p_res = await db.execute(select(Product).filter(Product.id == order.product_id))
    product = p_res.scalar_one_or_none()
    lic_res = await db.execute(select(License).filter(License.order_id == order.id))
    lic = lic_res.scalar_one_or_none()
    pmt_res = await db.execute(select(InstallmentPayment).filter(InstallmentPayment.order_id == order.id).order_by(InstallmentPayment.payment_number.asc()))
    payments = pmt_res.scalars().all()
    return InstallmentCustomerResponse(
        order_id=order.id, mt5_id=lic.mt5_id if lic else order.mt5_id,
        product_name=product.name if product else "EA",
        total_amount=order.installment_total_amount or 0, installment_amount=order.installment_amount or 0,
        amount_paid=order.amount_paid or 0, amount_remaining=order.amount_remaining or 0,
        installments_paid=order.installments_paid or 0, installment_count=order.installment_count or 0,
        license_status=lic.status if lic else "None", license_expiry=lic.expiry_date if lic else None,
        next_due_date=order.next_due_date, installment_status=order.installment_status or "active",
        license_period_days=order.license_period_days,
        payments=[InstallmentPaymentRecord.model_validate(p) for p in payments]
    )

@router.get("/admin/all", response_model=List[InstallmentCustomerResponse])
async def get_all_installments(db: AsyncSession = Depends(get_db)):
    stmt = select(Order).filter(Order.installment_enabled == True)
    result = await db.execute(stmt)
    orders = result.scalars().all()
    responses = []
    for order in orders:
        lic_res = await db.execute(select(License).filter(License.order_id == order.id))
        lic = lic_res.scalar_one_or_none()
        prod_res = await db.execute(select(Product).filter(Product.id == order.product_id))
        prod = prod_res.scalar_one_or_none()
        pay_res = await db.execute(select(InstallmentPayment).filter(InstallmentPayment.order_id == order.id).order_by(InstallmentPayment.payment_number))
        payments = pay_res.scalars().all()
        responses.append({
            "order_id": order.id, "mt5_id": order.mt5_id,
            "product_name": prod.name if prod else "Unknown Product",
            "total_amount": order.installment_total_amount or 0, "installment_amount": order.installment_amount or 0,
            "amount_paid": order.amount_paid or 0, "amount_remaining": order.amount_remaining or 0,
            "installments_paid": order.installments_paid or 0, "installment_count": order.installment_count or 0,
            "license_status": lic.status if lic else "none", "license_expiry": lic.expiry_date if lic else None,
            "next_due_date": order.next_due_date, "installment_status": order.installment_status or "active",
            "license_period_days": order.license_period_days,
            "payments": [InstallmentPaymentRecord.model_validate(p) for p in payments]
        })
    return responses

@router.post("/admin/disable/{order_id}")
async def disable_installment_arrangement(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order or not order.installment_enabled:
        raise HTTPException(status_code=404, detail="Installment arrangement not found")
    order.installment_status = "failed"
    order.status = "failed"
    lic_res = await db.execute(select(License).filter(License.order_id == order_id))
    lic = lic_res.scalar_one_or_none()
    if lic:
        lic.status = "expired"
    await db.commit()
    return {"status": "success", "message": "Installment arrangement disabled and license revoked"}

@router.get("/admin/{order_id}", response_model=InstallmentCustomerResponse)
async def get_admin_installment(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order or not order.installment_enabled:
        raise HTTPException(status_code=404, detail="Installment arrangement not found")
    p_res = await db.execute(select(Product).filter(Product.id == order.product_id))
    product = p_res.scalar_one_or_none()
    lic_res = await db.execute(select(License).filter(License.order_id == order.id))
    lic = lic_res.scalar_one_or_none()
    pmt_res = await db.execute(select(InstallmentPayment).filter(InstallmentPayment.order_id == order.id).order_by(InstallmentPayment.payment_number.asc()))
    payments = pmt_res.scalars().all()
    return InstallmentCustomerResponse(
        order_id=order.id, mt5_id=lic.mt5_id if lic else order.mt5_id,
        product_name=product.name if product else "EA",
        total_amount=order.installment_total_amount or 0, installment_amount=order.installment_amount or 0,
        amount_paid=order.amount_paid or 0, amount_remaining=order.amount_remaining or 0,
        installments_paid=order.installments_paid or 0, installment_count=order.installment_count or 0,
        license_status=lic.status if lic else "None", license_expiry=lic.expiry_date if lic else None,
        next_due_date=order.next_due_date, installment_status=order.installment_status or "active",
        license_period_days=order.license_period_days,
        payments=[InstallmentPaymentRecord.model_validate(p) for p in payments]
    )
