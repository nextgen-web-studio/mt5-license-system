import os

def update_endpoint(filepath, search_str, replacement):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(search_str, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

lic_search = '''@router.delete("/{license_id}")
async def delete_license(license_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
        
    # TODO: Revoke from server if active
    
    await db.delete(license_obj)
    await db.commit()
    return {"status": "success", "message": "License deleted"}'''

lic_repl = '''@router.delete("/{license_id}")
async def delete_license(license_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
        
    from app.models import CompileJob, TrialActivation, TrialClaim, LicenseMt5History, BrokerChangeRequest
    await db.execute(CompileJob.__table__.delete().where(CompileJob.license_id == license_id))
    await db.execute(TrialActivation.__table__.delete().where(TrialActivation.license_id == license_id))
    await db.execute(TrialClaim.__table__.delete().where(TrialClaim.license_id == license_id))
    await db.execute(LicenseMt5History.__table__.delete().where(LicenseMt5History.license_id == license_id))
    await db.execute(BrokerChangeRequest.__table__.delete().where(BrokerChangeRequest.license_id == license_id))
    
    await db.delete(license_obj)
    await db.commit()
    return {"status": "success", "message": "License deleted"}'''

update_endpoint('backend/app/api/v1/endpoints/licenses.py', lic_search, lic_repl)

ord_search = '''@router.delete("/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
    return {"status": "success", "message": "Order deleted"}'''

ord_repl = '''@router.delete("/{order_id}")
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
    return {"status": "success", "message": "Order deleted"}'''

update_endpoint('backend/app/api/v1/endpoints/orders.py', ord_search, ord_repl)
