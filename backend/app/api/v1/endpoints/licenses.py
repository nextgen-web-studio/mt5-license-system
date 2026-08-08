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
