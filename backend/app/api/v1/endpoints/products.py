from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models import Product
from app.schemas import ProductResponse, ProductCreate, ProductUpdate

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

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_update: ProductUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
        
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Soft delete
    db_product.active = False
    await db.commit()
    return {"status": "success", "message": "Product deleted successfully"}
import httpx, os
from fastapi import APIRouter as _ar

_exchange_router = _ar()

@_exchange_router.get("/exchange-rate")
async def get_usd_inr_rate():
    """Fetch live USD to INR exchange rate from public API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get("https://v6.exchangerate-api.com/v6/6494af2284407a5967a272d7/latest/USD")
            if res.status_code == 200:
                data = res.json()
                rate = data["conversion_rates"]["INR"]
                return {"rate": rate, "source": "frankfurter.app", "base": "USD"}
    except Exception:
        pass
    # Fallback to a reasonable static rate
    return {"rate": 84.0, "source": "fallback", "base": "USD"}
