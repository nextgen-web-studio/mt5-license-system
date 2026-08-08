import uuid
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    name = Column(String)
    username = Column(String)
    phone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, index=True) # 'EA' or 'VPS'
    name = Column(String, index=True)
    price = Column(Float)
    duration = Column(Integer) # in months
    active = Column(Boolean, default=True)
    description = Column(Text)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    order_type = Column(String) # 'EA' or 'VPS'
    mt5_id = Column(String, nullable=True) # captured before payment
    # pending, paid, compiling, ready, delivered, expired, cancelled
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    razorpay_order_id = Column(String, unique=True)
    payment_id = Column(String)
    amount = Column(Float)
    status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    mt5_id = Column(String)
    purchase_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True))
    license_uuid = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    generated_filename = Column(String) # This will be the path to the ZIP file
    download_count = Column(Integer, default=0)
    renew_count = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CompileJob(Base):
    __tablename__ = "compile_jobs"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("licenses.id"))
    status = Column(String, default="pending") # pending, processing, completed, failed
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class VpsOrder(Base):
    __tablename__ = "vps_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    duration = Column(Integer)
    status = Column(String, default="pending")
    ip = Column(String)
    username = Column(String)
    password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    message = Column(Text)
    status = Column(String, default="unread")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
