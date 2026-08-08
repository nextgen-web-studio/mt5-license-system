from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import products, payments, users, licenses, orders, admin

from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.cron.expire_licenses import run_expiration_check

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_expiration_check, 'interval', hours=12)
    scheduler.start()
    # Also run it immediately on startup
    scheduler.add_job(run_expiration_check)
    yield
    scheduler.shutdown()

app = FastAPI(title="Infinity Trader API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(licenses.router, prefix="/api/v1/licenses", tags=["licenses"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Infinity Trader API"}

@app.get("/migrate")
async def run_migrations():
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("ALTER TABLE orders ADD COLUMN mt5_id VARCHAR"))
            await session.commit()
            return {"status": "success", "message": "Successfully added mt5_id column to orders table."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Infinity Trader API",
        "version": "1.0.0"
    }
