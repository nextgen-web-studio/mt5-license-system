from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from pydantic import BaseModel

from app.db.database import get_db
from app.models import AdminSettings
from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

class LoginRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

async def get_or_create_admin_hash(db: AsyncSession) -> str:
    stmt = select(AdminSettings).where(AdminSettings.setting_key == "admin_password")
    result = await db.execute(stmt)
    setting = result.scalars().first()
    
    if not setting:
        # Create default hash for 'infinity trader'
        default_hash = get_password_hash("infinity trader")
        setting = AdminSettings(setting_key="admin_password", setting_value=default_hash)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        
    return setting.setting_value

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    hashed_password = await get_or_create_admin_hash(db)
    
    if not verify_password(req.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(AdminSettings).where(AdminSettings.setting_key == "admin_password")
    result = await db.execute(stmt)
    setting = result.scalars().first()
    
    if not setting:
        raise HTTPException(status_code=500, detail="Admin settings not initialized")
        
    if not verify_password(req.old_password, setting.setting_value):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password",
        )
        
    setting.setting_value = get_password_hash(req.new_password)
    await db.commit()
    
    return {"status": "success", "message": "Password updated successfully"}
