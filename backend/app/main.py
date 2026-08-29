from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.v1.endpoints import auth, products, users, licenses, orders, admin, jobs, trials, settings, installments, ea_templates

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
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        from app.db.database import AsyncSessionLocal
        from app.models import Product
        from sqlalchemy import update
        async with AsyncSessionLocal() as session:
            await session.execute(update(Product).where(Product.type == "EA").values(price=500.0))
            await session.commit()
            print("Successfully updated EA product price to 500")
    except Exception as e:
        print(f"Failed to update EA price: {e}")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(licenses.router, prefix="/api/v1/licenses", tags=["licenses"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(trials.router, prefix="/api/v1/trials", tags=["trials"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(installments.router, prefix="/api/v1/installments", tags=["installments"])
app.include_router(ea_templates.router, prefix="/api/v1/ea-templates", tags=["ea-templates"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Infinity Trader API"}



@app.get("/health")
@app.head("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Infinity Trader API",
        "version": "1.0.0"
    }

