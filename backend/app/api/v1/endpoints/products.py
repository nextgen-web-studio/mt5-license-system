from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models import Product
from app.schemas import ProductResponse, ProductCreate

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.active == True))
    products = result.scalars().all()
    return products

@router.post("/", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    db_product = Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product
