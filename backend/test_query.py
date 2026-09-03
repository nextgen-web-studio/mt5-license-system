import asyncio
from sqlalchemy import text
from app.db.database import engine, AsyncSessionLocal

async def test_query():
    async with AsyncSessionLocal() as db:
        try:
            from app.models import VpsOrder, Order, User, Product
            from sqlalchemy.future import select
            result = await db.execute(
                select(VpsOrder, Order, User, Product)
                .join(Order, VpsOrder.order_id == Order.id)
                .join(User, VpsOrder.user_id == User.id)
                .join(Product, Order.product_id == Product.id)
                .order_by(VpsOrder.created_at.desc())
            )
            print("Query successful", len(result.all()))
        except Exception as e:
            print("Query Error:", e)

if __name__ == "__main__":
    asyncio.run(test_query())
