import asyncio
from sqlalchemy import text
from app.db.database import engine

async def migrate():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE orders ADD COLUMN vps_id INTEGER REFERENCES vps_orders(id);"))
            print("Migration successful")
        except Exception as e:
            print("Error or already migrated:", e)

if __name__ == "__main__":
    asyncio.run(migrate())
