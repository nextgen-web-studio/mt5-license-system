import os
import re

filepath = 'backend/app/api/v1/endpoints/installments.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_endpoints = """

@router.get("/admin/all", response_model=List[InstallmentCustomerResponse])
async def get_all_installments(db: AsyncSession = Depends(get_db)):
    # Fetch all orders with installment_enabled = True
    stmt = select(Order).filter(Order.installment_enabled == True)
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    responses = []
    for order in orders:
        # Get License
        lic_res = await db.execute(select(License).filter(License.order_id == order.id))
        lic = lic_res.scalar_one_or_none()
        
        # Get Product
        prod_res = await db.execute(select(Product).filter(Product.id == order.product_id))
        prod = prod_res.scalar_one_or_none()
        product_name = prod.name if prod else "Unknown Product"
        
        # Get Payments
        pay_res = await db.execute(select(InstallmentPayment).filter(InstallmentPayment.order_id == order.id).order_by(InstallmentPayment.payment_number))
        payments = pay_res.scalars().all()
        
        responses.append({
            "order_id": order.id,
            "mt5_id": order.mt5_id,
            "product_name": product_name,
            "total_amount": order.installment_total_amount or 0,
            "installment_amount": order.installment_amount or 0,
            "amount_paid": order.amount_paid or 0,
            "amount_remaining": order.amount_remaining or 0,
            "installments_paid": order.installments_paid or 0,
            "installment_count": order.installment_count or 0,
            "license_status": lic.status if lic else "none",
            "license_expiry": lic.expiry_date if lic else None,
            "next_due_date": order.next_due_date,
            "installment_status": order.installment_status or "active",
            "license_period_days": order.license_period_days,
            "payments": payments
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
"""

if "def get_all_installments" not in content:
    content += new_endpoints
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
