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
    order_id: Optional[int] = None
    user_id: int
    mt5_id: str
    license_uuid: str
    status: str
    purchase_date: datetime
    expiry_date: Optional[datetime] = None
    download_count: int
    renew_count: int
    license_type: str = "paid"
    
    class Config:
        from_attributes = True

class LicenseCreate(BaseModel):
    order_id: int
    mt5_id: str

from typing import Optional

class LicenseUpdate(BaseModel):
    mt5_id: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[datetime] = None
    purchase_date: Optional[datetime] = None
    download_count: Optional[int] = None
    renew_count: Optional[int] = None

router = APIRouter()

@router.put("/{license_id}", response_model=LicenseResponse)
async def update_license(license_id: int, update_data: LicenseUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
        
    if update_data.mt5_id is not None:
        license_obj.mt5_id = update_data.mt5_id
    if update_data.status is not None:
        license_obj.status = update_data.status
    if update_data.expiry_date is not None:
        license_obj.expiry_date = update_data.expiry_date
    if update_data.purchase_date is not None:
        license_obj.purchase_date = update_data.purchase_date
    if update_data.download_count is not None:
        license_obj.download_count = update_data.download_count
    if update_data.renew_count is not None:
        license_obj.renew_count = update_data.renew_count
        
    await db.commit()
    await db.refresh(license_obj)
    return license_obj

@router.post("/", response_model=LicenseResponse)
async def generate_license(license_in: LicenseCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
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
    
    background_tasks.add_task(start_azure_vm_if_needed)
    
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

@router.get("/telegram/{telegram_id}", response_model=List[LicenseResponse])
async def get_telegram_licenses(telegram_id: str, db: AsyncSession = Depends(get_db)):
    from app.models import User, TrialActivation
    
    # 1. Get user id from telegram id
    user_res = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    user = user_res.scalar_one_or_none()
    
    licenses = []
    
    # 2. Get paid licenses
    if user:
        lic_res = await db.execute(select(License).filter(License.user_id == user.id).order_by(License.created_at.desc()))
        licenses.extend(lic_res.scalars().all())
        
    # 3. Get trial licenses
    trial_res = await db.execute(select(TrialActivation).filter(TrialActivation.telegram_user_id == telegram_id))
    activations = trial_res.scalars().all()
    
    if activations:
        trial_ids = [a.license_id for a in activations]
        trial_lic_res = await db.execute(select(License).filter(License.id.in_(trial_ids)))
        licenses.extend(trial_lic_res.scalars().all())
        
    return licenses

from fastapi.responses import FileResponse
import os

@router.get("/{license_id}/download")
async def download_license(license_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
        
    file_path = license_obj.generated_filename
    if not file_path:
        raise HTTPException(status_code=400, detail="License file not generated yet")
        
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")
    
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        # We can either stream it or generate a signed URL and redirect.
        # Generating a public URL or signed URL is easiest.
        bucket_name = "licenses"
        url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch license file: {e}")

@router.get("/{license_id}/delivery-info")
async def get_delivery_info(license_id: int, db: AsyncSession = Depends(get_db)):
    # Returns telegram_id, mt5_id, and download_url
    result = await db.execute(select(License).filter(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
        
    usr_res = await db.execute(select(User).filter(User.id == lic.user_id))
    usr = usr_res.scalar_one_or_none()
    if not usr:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Get supabase URL
    file_path = lic.generated_filename
    url = ""
    if file_path:
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY")
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            
            signed_res = supabase.storage.from_("licenses").create_signed_url(file_path, 3600)
            if isinstance(signed_res, str):
                url = signed_res
            elif isinstance(signed_res, dict):
                url = signed_res.get("signedURL") or signed_res.get("signedUrl") or ""
            else:
                url = getattr(signed_res, "signedURL", getattr(signed_res, "signedUrl", ""))
                
        except Exception as e:
            print(f"Error generating signed URL: {e}")
            
    return {
        "telegram_id": usr.telegram_id,
        "mt5_id": lic.mt5_id,
        "download_url": url
    }

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
