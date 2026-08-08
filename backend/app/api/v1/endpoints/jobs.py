from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import os
import uuid
from datetime import datetime

from app.db.database import get_db
from app.models import CompileJob, License, Order

router = APIRouter()

@router.get("/pending")
async def get_pending_jobs(db: AsyncSession = Depends(get_db)):
    """
    Windows Worker polls this endpoint to get pending compilation jobs.
    """
    result = await db.execute(select(CompileJob).filter(CompileJob.status == "pending").limit(10))
    jobs = result.scalars().all()
    
    response_jobs = []
    for job in jobs:
        # Get associated license to know what MT5 ID to compile for
        lic_res = await db.execute(select(License).filter(License.id == job.license_id))
        lic = lic_res.scalar_one_or_none()
        if lic:
            response_jobs.append({
                "job_id": job.id,
                "license_id": job.license_id,
                "mt5_id": lic.mt5_id,
                "created_at": job.created_at
            })
            
    return response_jobs

@router.post("/{job_id}/claim")
async def claim_job(job_id: int, worker_id: str, db: AsyncSession = Depends(get_db)):
    """
    Worker claims a job so no other worker picks it up.
    """
    result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "pending":
        raise HTTPException(status_code=400, detail="Job is not pending")
        
    job.status = "processing"
    job.worker_id = worker_id
    job.started_at = datetime.utcnow()
    await db.commit()
    return {"status": "success", "message": "Job claimed"}

@router.post("/{job_id}/upload")
async def upload_compiled_file(job_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Worker uploads the compiled .ex5 file (zipped).
    """
    result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Read file
    content = await file.read()
    
    # Save locally (Temporary/Ephemeral on Render)
    os.makedirs("downloads", exist_ok=True)
    filename = f"downloads/EA_License_Job_{job.id}.zip"
    with open(filename, "wb") as f:
        f.write(content)
        
    # Attempt to upload to Supabase if configured (Persistent)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            bucket_name = "licenses"
            # Ensure bucket exists or just upload
            file_path = f"ea_{job.id}_{uuid.uuid4().hex[:8]}.zip"
            supabase.storage.from_(bucket_name).upload(file_path, content)
            
            # Get public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            # You could save public_url to the DB here if needed
        except Exception as e:
            print(f"Failed to upload to Supabase: {e}")
            
    # Update Job & License & Order
    job.status = "completed"
    
    lic_res = await db.execute(select(License).filter(License.id == job.license_id))
    lic = lic_res.scalar_one_or_none()
    if lic:
        lic.generated_filename = filename
        lic.status = "active"
        
        ord_res = await db.execute(select(Order).filter(Order.id == lic.order_id))
        ord_obj = ord_res.scalar_one_or_none()
        if ord_obj:
            ord_obj.status = "delivered"
            
    await db.commit()
    return {"status": "success"}
