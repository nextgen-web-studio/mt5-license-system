from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import datetime
from dateutil.relativedelta import relativedelta

from app.db.database import get_db
from app.models import TrialSetting, TrialActivation, License, CompileJob
from pydantic import BaseModel
from app.core.azure_vm import start_azure_vm_if_needed

router = APIRouter()

class TrialSettingSchema(BaseModel):
    enabled: bool
    duration_days: int
    max_trials_per_month: int
    allow_existing_customers: bool
    trial_plan_name: str
    
    class Config:
        from_attributes = True

class TrialRequest(BaseModel):
    telegram_user_id: str
    mt5_id: str

@router.get("/settings", response_model=TrialSettingSchema)
async def get_trial_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrialSetting).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        # Return defaults if not seeded
        return TrialSettingSchema(
            enabled=True,
            duration_days=2,
            max_trials_per_month=2,
            allow_existing_customers=False,
            trial_plan_name="Trial EA"
        )
    return settings

@router.put("/settings", response_model=TrialSettingSchema)
async def update_trial_settings(settings_in: TrialSettingSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrialSetting).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = TrialSetting(
            enabled=settings_in.enabled,
            duration_days=settings_in.duration_days,
            max_trials_per_month=settings_in.max_trials_per_month,
            allow_existing_customers=settings_in.allow_existing_customers,
            trial_plan_name=settings_in.trial_plan_name
        )
        db.add(settings)
    else:
        settings.enabled = settings_in.enabled
        settings.duration_days = settings_in.duration_days
        settings.max_trials_per_month = settings_in.max_trials_per_month
        settings.allow_existing_customers = settings_in.allow_existing_customers
        settings.trial_plan_name = settings_in.trial_plan_name
        
    await db.commit()
    await db.refresh(settings)
    return settings

@router.post("/request")
async def request_free_trial(req: TrialRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # 1. Check if trial is globally enabled
    settings_res = await db.execute(select(TrialSetting).limit(1))
    settings = settings_res.scalar_one_or_none()
    
    # Defaults if missing
    enabled = settings.enabled if settings else True
    duration_days = settings.duration_days if settings else 2
    max_trials = settings.max_trials_per_month if settings else 2
    allow_existing = settings.allow_existing_customers if settings else False
    plan_name = settings.trial_plan_name if settings else "Trial EA"

    if not enabled:
        raise HTTPException(status_code=400, detail="Free Trial is currently unavailable. Please check again later.")

    # 2. Check if MT5 ID has an active paid license
    if not allow_existing:
        existing_paid = await db.execute(
            select(License).filter(
                License.mt5_id == req.mt5_id,
                License.license_type == "paid",
                License.status == "active"
            )
        )
        if existing_paid.scalars().first():
            raise HTTPException(status_code=400, detail="This MT5 ID already has an active license.")

    # 3. Check Monthly limits
    current_time = datetime.datetime.now()
    month_key = current_time.strftime("%Y-%m")
    
    # Count trials for this telegram ID this month
    tg_trials = await db.execute(
        select(TrialActivation).filter(
            TrialActivation.telegram_user_id == req.telegram_user_id,
            TrialActivation.month_key == month_key
        )
    )
    tg_count = len(tg_trials.scalars().all())
    if tg_count >= max_trials:
        raise HTTPException(status_code=400, detail=f"You have already used your {max_trials} free trials this month.")

    # Count trials for this MT5 ID this month (to prevent abuse with multiple TG accounts)
    mt5_trials = await db.execute(
        select(TrialActivation).filter(
            TrialActivation.mt5_id == req.mt5_id,
            TrialActivation.month_key == month_key
        )
    )
    mt5_count = len(mt5_trials.scalars().all())
    if mt5_count >= max_trials:
        raise HTTPException(status_code=400, detail=f"This MT5 ID has already reached the maximum of {max_trials} free trials this month.")

    # 4. Create License and Activation
    expiry = current_time + relativedelta(days=duration_days)
    
    db_license = License(
        user_id=1, # Assign to admin or standard system user since trials aren't full users
        mt5_id=req.mt5_id,
        expiry_date=expiry,
        status="generating",
        license_type="trial"
    )
    db.add(db_license)
    await db.commit()
    await db.refresh(db_license)

    activation = TrialActivation(
        telegram_user_id=req.telegram_user_id,
        mt5_id=req.mt5_id,
        license_id=db_license.id,
        started_at=current_time,
        expires_at=expiry,
        month_key=month_key,
        status="active"
    )
    db.add(activation)
    await db.commit()

    # 5. Enqueue compile job
    job = CompileJob(license_id=db_license.id, status="pending")
    db.add(job)
    await db.commit()

    background_tasks.add_task(start_azure_vm_if_needed)
    
    return {
        "status": "success",
        "message": "Trial Approved! Preparing EA...",
        "license_id": db_license.id,
        "expiry_date": expiry.strftime("%d %b %Y"),
        "duration_days": duration_days
    }
