from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from datetime import datetime, timezone
from typing import List

from app.db.database import get_db
from app.models import Offer, Product
from app.schemas import OfferCreate, OfferUpdate, OfferResponse

router = APIRouter()


def _now():
    return datetime.now(timezone.utc)


@router.get("", response_model=List[OfferResponse])
async def list_offers(db: AsyncSession = Depends(get_db)):
    """List all offers (including expired/inactive) for the admin dashboard."""
    result = await db.execute(select(Offer).order_by(Offer.created_at.desc()))
    return result.scalars().all()


@router.get("/active", response_model=List[OfferResponse])
async def list_active_offers(db: AsyncSession = Depends(get_db)):
    """List only currently active, non-expired offers."""
    now = _now()
    result = await db.execute(
        select(Offer).where(
            and_(
                Offer.active == True,
                Offer.starts_at <= now,
                Offer.expires_at >= now,
            )
        )
    )
    return result.scalars().all()


@router.post("", response_model=OfferResponse)
async def create_offer(offer: OfferCreate, db: AsyncSession = Depends(get_db)):
    """Create a new flash sale offer for a product."""
    # Validate the product exists
    product = await db.get(Product, offer.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if offer.offer_price >= product.price:
        raise HTTPException(
            status_code=400,
            detail="Offer price must be lower than the original product price"
        )

    if offer.expires_at <= offer.starts_at:
        raise HTTPException(status_code=400, detail="expires_at must be after starts_at")

    db_offer = Offer(
        product_id=offer.product_id,
        offer_label=offer.offer_label,
        offer_price=offer.offer_price,
        starts_at=offer.starts_at,
        expires_at=offer.expires_at,
        active=offer.active,
    )
    db.add(db_offer)
    await db.commit()
    await db.refresh(db_offer)
    return db_offer


@router.put("/{offer_id}", response_model=OfferResponse)
async def update_offer(offer_id: int, offer_update: OfferUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing offer."""
    db_offer = await db.get(Offer, offer_id)
    if not db_offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    update_data = offer_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_offer, key, value)

    await db.commit()
    await db.refresh(db_offer)
    return db_offer


@router.delete("/{offer_id}")
async def delete_offer(offer_id: int, db: AsyncSession = Depends(get_db)):
    """Delete (hard delete) an offer."""
    db_offer = await db.get(Offer, offer_id)
    if not db_offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    await db.delete(db_offer)
    await db.commit()
    return {"status": "success", "message": "Offer deleted"}
