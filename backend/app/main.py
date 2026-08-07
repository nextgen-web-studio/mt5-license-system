from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import products, payments, users, licenses, orders, admin

app = FastAPI(title="Infinity Trader API")

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
