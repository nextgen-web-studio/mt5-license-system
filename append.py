import os
def append_to(path, text):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(text)

order_endpoint = '''
@router.delete("/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
    return {"status": "success", "message": "Order deleted"}
'''
append_to('backend/app/api/v1/endpoints/orders.py', order_endpoint)

ea_endpoint = '''
@router.delete("/admin/{template_id}")
async def delete_ea_template(template_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EaTemplate).filter(EaTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(t)
    await db.commit()
    return {"status": "success", "message": "Template deleted"}
'''
append_to('backend/app/api/v1/endpoints/ea_templates.py', ea_endpoint)
