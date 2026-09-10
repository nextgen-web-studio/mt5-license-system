from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductBase(BaseModel):
    type: str
    name: str
    price: float
    duration: int
    active: bool = True
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    duration: Optional[int] = None
    active: Optional[bool] = None
    description: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    product_id: int
    order_type: str
    mt5_id: Optional[str] = None
    vps_id: Optional[int] = None

class OrderCreate(OrderBase):
    user_id: int

class OrderResponse(OrderBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    
class PaymentResponse(BaseModel):
    id: int
    payment_id: Optional[str]
    amount: float
    status: str
    
    class Config:
        from_attributes = True

class CompileJobResponse(BaseModel):
    id: int
    license_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrderFulfillmentRequest(BaseModel):
    mt5_id: Optional[str] = None
    vps_id: Optional[int] = None

class OfferCreate(BaseModel):
    product_id: int
    offer_label: str
    offer_price: float
    starts_at: datetime
    expires_at: datetime
    active: bool = True

class OfferUpdate(BaseModel):
    offer_label: Optional[str] = None
    offer_price: Optional[float] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    active: Optional[bool] = None

class OfferResponse(BaseModel):
    id: int
    product_id: int
    offer_label: str
    offer_price: float
    starts_at: datetime
    expires_at: datetime
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProductWithOfferResponse(BaseModel):
    id: int
    type: str
    name: str
    price: float
    duration: int
    active: bool
    description: Optional[str] = None
    # Offer fields — None if no active offer
    offer_id: Optional[int] = None
    offer_label: Optional[str] = None
    offer_price: Optional[float] = None
    offer_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

