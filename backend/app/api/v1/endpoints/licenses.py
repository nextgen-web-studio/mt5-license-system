from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import csv
import io

from app.db.database import get_db
from app.models import License, Order, Product, CompileJob, User, Payment
from pydantic import BaseModel
from datetime import datetime
from app.core.local_compiler import local_wine_compiler

class LicenseResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    user_id: int
    telegram_id: Optional[str] = None
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


class LicenseUpdate(BaseModel):
    mt5_id: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[datetime] = None
    purchase_date: Optional[datetime] = None
    download_count: Optional[int] = None
    renew_count: Optional[int] = None
    broker: Optional[str] = None

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
    if update_data.broker is not None:
        license_obj.broker = update_data.broker
        
    await db.commit()
    await db.refresh(license_obj)
    return license_obj

@router.post("/generate", response_model=LicenseResponse)
async def generate_license(license_in: LicenseCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Fetch order and verify it's in an approvable state
        result = await db.execute(select(Order).filter(Order.id == license_in.order_id))
        order = result.scalar_one_or_none()
        
        if not order or order.status not in ("approved_waiting_for_mt5_id", "compiling", "delivered", "approved"):
            raise HTTPException(status_code=400, detail="Order not found or not approved")
            
        # 2. Get product duration
        prod_result = await db.execute(select(Product).filter(Product.id == order.product_id))
        product = prod_result.scalar_one_or_none()
        
        if not product or product.type != "EA":
            raise HTTPException(status_code=400, detail="Invalid product type for license")
            
        from datetime import datetime, timezone
        from dateutil.relativedelta import relativedelta
        import uuid
        import logging
        
        # Handle Lifetime Plan (duration=0 or >=999 means lifetime, no expiry)
        if product.duration == 0 or product.duration >= 999:
            expiry = None
        else:
            expiry = datetime.now(timezone.utc) + relativedelta(months=product.duration)
        
        # 3. Check for Duplicate MT5 ID
        from sqlalchemy import and_
        dup_stmt = select(License).filter(
            and_(
                License.mt5_id == license_in.mt5_id,
                License.order_id != order.id,
                License.status.in_(["active", "generating", "pending", "compiling"])
            )
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.first():
            raise HTTPException(status_code=400, detail="This MT5 ID is already registered to another active license in the system.")

        # 4. Create or Update License
        lic_result = await db.execute(select(License).filter(License.order_id == order.id))
        db_license = lic_result.scalar_one_or_none()
        
        if db_license:
            db_license.mt5_id = license_in.mt5_id
            db_license.expiry_date = expiry
            db_license.status = "generating"
        else:
            db_license = License(
                order_id=order.id,
                user_id=order.user_id,
                mt5_id=license_in.mt5_id,
                expiry_date=expiry,
                status="generating",
                license_uuid=str(uuid.uuid4())
            )
            db.add(db_license)
            await db.flush()
        
        # 4. Enqueue compilation job (only if not already pending/processing)
        existing_job_res = await db.execute(
            select(CompileJob).filter(
                CompileJob.license_id == db_license.id,
                CompileJob.status.in_(["pending", "processing"])
            )
        )
        if existing_job_res.first() is None:
            job = CompileJob(license_id=db_license.id, status="pending")
            db.add(job)
            await db.flush()
            background_tasks.add_task(local_wine_compiler, job.id)
        
        order.status = "compiling"
        
        await db.commit()
        
        # Send Compiling notification to TG
        import os, httpx, asyncio
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        try:
            if bot_token:
                from app.models import User
                u_res = await db.execute(select(User).filter(User.id == order.user_id))
                u = u_res.scalar_one_or_none()
                if u and u.telegram_id:
                    from app.core.telegram_animator import animate_compiling
                    asyncio.create_task(animate_compiling(bot_token, u.telegram_id, db_license.id))
        except Exception as e:
            logging.error(f"Failed to send compiling notification: {e}")
        await db.refresh(db_license)
        
        lic_dict = {c.name: getattr(db_license, c.name) for c in db_license.__table__.columns}
        lic_dict["telegram_id"] = u.telegram_id if u else None
        return lic_dict
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"[LICENSE GENERATE] DB Error: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database or Server Error during license generation: {str(e)}")

@router.get("/", response_model=List[LicenseResponse])
async def list_licenses(db: AsyncSession = Depends(get_db)):
    from app.models import User
    result = await db.execute(
        select(License, User.telegram_id)
        .outerjoin(User, License.user_id == User.id)
        .order_by(License.created_at.desc())
    )
    rows = result.all()
    licenses = []
    for lic, t_id in rows:
        lic_dict = {c.name: getattr(lic, c.name) for c in lic.__table__.columns}
        lic_dict["telegram_id"] = t_id
        licenses.append(lic_dict)
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

@router.get("/export/csv")
async def export_licenses_csv(db: AsyncSession = Depends(get_db)):
    # Query: User.name, Order.product_id, License.mt5_id, Payment.payment_id (or payment_id)
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
    writer.writerow(["Customer Name", "Product ID", "License (MT5 ID)", "Payment ID"])
    
    for row in rows:
        name = row[0] or "Unknown"
        product_id = row[1]
        mt5_id = row[2]
        payment_id = row[3] or "N/A"
        writer.writerow([name, product_id, mt5_id, payment_id])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=licenses_export.csv"}
    )
class BrokerChangePayload(BaseModel):
    new_mt5_id: str
    new_broker: str
    telegram_id: str

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

@router.post("/{license_id}/recompile")
async def recompile_license(license_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).filter(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
        
    lic.status = "generating"
    
    # Create new CompileJob only if not pending
    existing_job_res = await db.execute(
        select(CompileJob).filter(
            CompileJob.license_id == lic.id,
            CompileJob.status.in_(["pending", "processing"])
        )
    )
    if existing_job_res.first() is None:
        job = CompileJob(license_id=lic.id, status="pending")
        db.add(job)
        await db.commit()
        from app.core.local_compiler import local_wine_compiler
        background_tasks.add_task(local_wine_compiler, job.id)
    else:
        await db.commit()
    
    # Get job_id safely
    job_result = await db.execute(
        select(CompileJob).filter(
            CompileJob.license_id == lic.id,
            CompileJob.status.in_(["pending", "processing"])
        ).order_by(CompileJob.id.desc())
    )
    latest_job = job_result.scalars().first()
    
    import os, httpx, asyncio
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    try:
        user_res = await db.execute(select(User).filter(User.id == lic.user_id))
        user = user_res.scalar_one_or_none()
        if user and user.telegram_id and bot_token:
            from app.core.telegram_animator import animate_compiling
            asyncio.create_task(animate_compiling(bot_token, user.telegram_id, lic.id))
    except Exception as e:
        print(f"Failed to send recompile notification: {e}")
    
    return {"status": "success", "message": "Recompilation triggered", "job_id": latest_job.id if latest_job else None}

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

@router.delete("/{license_id}")
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


    return {"status": "success", "message": "License deleted"}



@router.post("/{license_id}/broker-change-request")
async def request_broker_change(license_id: int, payload: BrokerChangePayload, db: AsyncSession = Depends(get_db)):
    from app.models import BrokerChangeRequest, User
    
    try:
        # Verify user exists by telegram_id
        user_result = await db.execute(select(User).filter(User.telegram_id == payload.telegram_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=403, detail="Unauthorized: User not found")
            
        result = await db.execute(select(License).filter(License.id == license_id))
        lic = result.scalar_one_or_none()
        
        if not lic:
            raise HTTPException(status_code=404, detail="License not found")
            
        if lic.user_id != user.id:
            raise HTTPException(status_code=403, detail="Unauthorized: License does not belong to you")
            
        if lic.status != "active":
            raise HTTPException(status_code=400, detail="License must be active to request a broker change")
            
        if lic.license_type != "paid":
            raise HTTPException(status_code=400, detail="Only Lifetime (paid) licenses can request a broker change")
            
        if lic.mt5_id == payload.new_mt5_id:
            raise HTTPException(status_code=400, detail="New MT5 ID cannot be the same as the current one")
            
        if not payload.new_mt5_id:
            raise HTTPException(status_code=400, detail="New MT5 ID cannot be empty")
            
        # Check if the new MT5 ID is already registered elsewhere
        from sqlalchemy import and_
        dup_stmt = select(License).filter(
            and_(
                License.mt5_id == payload.new_mt5_id,
                License.status.in_(["active", "generating", "pending", "compiling"])
            )
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.first():
            raise HTTPException(status_code=400, detail="This MT5 ID is already registered to another active license in the system.")
            
        # Check for duplicate pending requests
        existing_req_result = await db.execute(
            select(BrokerChangeRequest)
            .filter(BrokerChangeRequest.license_id == license_id, BrokerChangeRequest.status == "pending_broker_change_approval")
        )
        if existing_req_result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="A broker change request is already pending for this license")
            
        req = BrokerChangeRequest(
            user_id=lic.user_id,
            license_id=lic.id,
            old_mt5_id=lic.mt5_id,
            old_broker=lic.broker,
            new_mt5_id=payload.new_mt5_id,
            new_broker=payload.new_broker,
            status="pending_broker_change_approval"
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        
        return {"status": "success", "request_id": req.id}
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Internal Error in broker-change-request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing your request")

@router.post("/broker-change/{request_id}/approve")
async def approve_broker_change(request_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from app.models import BrokerChangeRequest, LicenseMt5History, User
    from app.core.local_compiler import local_wine_compiler
    
    # 1. Fetch request and user
    result = await db.execute(select(BrokerChangeRequest).filter(BrokerChangeRequest.id == request_id))
    req = result.scalar_one_or_none()
    
    if not req or req.status != "pending_broker_change_approval":
        raise HTTPException(status_code=400, detail="Request not found or not pending")
        
    # 2. Fetch license
    lic_result = await db.execute(select(License).filter(License.id == req.license_id))
    lic = lic_result.scalar_one_or_none()
    
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
        
    user_result = await db.execute(select(User).filter(User.id == req.user_id))
    user = user_result.scalar_one_or_none()
        
    # 3. Create history
    history = LicenseMt5History(
        license_id=lic.id,
        old_mt5_id=lic.mt5_id,
        new_mt5_id=req.new_mt5_id,
        change_reason="Broker Change",
        approved_by="Admin"
    )
    db.add(history)
    
    # 4. Update license
    lic.mt5_id = req.new_mt5_id
    lic.broker = req.new_broker
    # Note: lifetime expiry remains NULL, no need to touch it
    
    # 5. Update request status
    req.status = "approved"
    
    # 6. Queue compile job
    job = CompileJob(license_id=lic.id, status="pending")
    db.add(job)
    
    await db.commit()
    
    background_tasks.add_task(local_wine_compiler, job.id)
    
    # Trigger compiling animation
    import os, asyncio, httpx
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token and user and user.telegram_id:
        from app.core.telegram_animator import animate_compiling
        asyncio.create_task(animate_compiling(bot_token, user.telegram_id, lic.id))
        
    # Trigger webhook to clear admin bot buttons
    try:
        async def call_webhook():
            async with httpx.AsyncClient() as client:
                bot_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-6gf3.onrender.com").replace("/internal/delivery", "").rstrip("/")
                await client.post(f"{bot_url}/internal/bc-approved", json={"request_id": request_id, "action": "approved"})
        asyncio.create_task(call_webhook())
    except:
        pass
        
    return {"status": "success", "telegram_id": user.telegram_id if user else None, "license_id": lic.id}

@router.post("/broker-change/{request_id}/reject")
async def reject_broker_change(request_id: int, db: AsyncSession = Depends(get_db)):
    from app.models import BrokerChangeRequest, User
    result = await db.execute(select(BrokerChangeRequest).filter(BrokerChangeRequest.id == request_id))
    req = result.scalar_one_or_none()
    
    if not req or req.status != "pending_broker_change_approval":
        raise HTTPException(status_code=400, detail="Request not found or not pending")
        
    req.status = "rejected"
    await db.commit()
    
    # Trigger webhook to clear admin bot buttons
    import asyncio, httpx
    try:
        async def call_webhook_reject():
            async with httpx.AsyncClient() as client:
                bot_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-6gf3.onrender.com").replace("/internal/delivery", "").rstrip("/")
                await client.post(f"{bot_url}/internal/bc-rejected", json={"request_id": request_id, "action": "rejected"})
        asyncio.create_task(call_webhook_reject())
    except:
        pass
    
    user_result = await db.execute(select(User).filter(User.id == req.user_id))
    user = user_result.scalar_one_or_none()
    
    return {"status": "success", "telegram_id": user.telegram_id if user else None}




