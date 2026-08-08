from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models import License, Order, Product, CompileJob
from pydantic import BaseModel
from datetime import datetime

class LicenseResponse(BaseModel):
    id: int
    order_id: int
    user_id: int
    mt5_id: str
    license_uuid: str
    status: str
    purchase_date: datetime
    expiry_date: datetime
    
    class Config:
        from_attributes = True

class LicenseCreate(BaseModel):
    order_id: int
    mt5_id: str

router = APIRouter()

@router.post("/", response_model=LicenseResponse)
async def generate_license(license_in: LicenseCreate, db: AsyncSession = Depends(get_db)):
    # 1. Fetch order and verify it's paid
    result = await db.execute(select(Order).filter(Order.id == license_in.order_id))
    order = result.scalar_one_or_none()
    
    if not order or order.status != "paid":
        raise HTTPException(status_code=400, detail="Order not found or not paid")
        
    # 2. Get product duration
    prod_result = await db.execute(select(Product).filter(Product.id == order.product_id))
    product = prod_result.scalar_one_or_none()
    
    if not product or product.type != "EA":
        raise HTTPException(status_code=400, detail="Invalid product type for license")
        
    # Calculate expiry (rough estimation based on 30 days per month)
    import datetime
    from dateutil.relativedelta import relativedelta
    expiry = datetime.datetime.now() + relativedelta(months=product.duration)
    
    # 3. Create License
    db_license = License(
        order_id=order.id,
        user_id=order.user_id,
        mt5_id=license_in.mt5_id,
        expiry_date=expiry,
        status="generating"
    )
    db.add(db_license)
    await db.commit()
    await db.refresh(db_license)
    
    # 4. Enqueue compilation job for background worker
    job = CompileJob(license_id=db_license.id, status="pending")
    db.add(job)
    await db.commit()
    
    return db_license

@router.get("/", response_model=List[LicenseResponse])
async def list_licenses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).order_by(License.created_at.desc()))
    licenses = result.scalars().all()
    return licenses

@router.get("/user/{user_id}", response_model=List[LicenseResponse])
async def get_user_licenses(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.user_id == user_id).order_by(License.created_at.desc()))
    licenses = result.scalars().all()
    return licenses

from fastapi.responses import FileResponse
import os

@router.get("/{license_id}/download")
async def download_license(license_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
        
    if not license_obj.generated_filename or not os.path.exists(license_obj.generated_filename):
        raise HTTPException(status_code=404, detail="Generated file not found on server")
        
    # Serve the file
    return FileResponse(
        path=license_obj.generated_filename,
        filename=os.path.basename(license_obj.generated_filename),
        media_type='application/zip'
    )

from datetime import timedelta
import csv
import io
from fastapi.responses import StreamingResponse
from app.models import User, Payment

@router.delete("/{license_id}")
async def delete_license(license_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
        
    if not license_obj.expiry_date:
        raise HTTPException(status_code=400, detail="License has no expiry date")
        
    now = datetime.utcnow()
    days_expired = (now - license_obj.expiry_date).days
    
    if days_expired < 5:
        raise HTTPException(status_code=400, detail="License must be expired for at least 5 days before deletion")
        
    await db.delete(license_obj)
    await db.commit()
    return {"status": "success", "message": "License deleted"}

@router.get("/export/csv")
async def export_licenses_csv(db: AsyncSession = Depends(get_db)):
    # Query: User.name, Order.product_id, License.mt5_id, Payment.razorpay_order_id (or payment_id)
    # Join License -> User
    # Join License -> Order -> Payment
    
    stmt = (
        select(User.name, Order.product_id, License.mt5_id, Payment.payment_id)
        .join(License, User.id == License.user_id)
        .join(Order, License.order_id == Order.id)
        .outerjoin(Payment, Order.id == Payment.order_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Customer Name", "Product ID", "License (MT5 ID)", "Razorpay ID"])
    
    for row in rows:
        name = row[0] or "Unknown"
        product_id = row[1]
        mt5_id = row[2]
        razorpay_id = row[3] or "N/A"
        writer.writerow([name, product_id, mt5_id, razorpay_id])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=licenses_export.csv"}
    )
