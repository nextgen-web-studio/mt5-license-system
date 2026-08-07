from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models import User
from pydantic import BaseModel
from datetime import datetime

from typing import Optional

class UserCreate(BaseModel):
    telegram_id: str
    name: str
    username: str
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    telegram_id: str
    name: str
    username: str
    phone: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.telegram_id == user.telegram_id))
    db_user = result.scalar_one_or_none()
    
    if db_user:
        return db_user # Return existing if already registered
        
    db_user = User(**user.dict())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
