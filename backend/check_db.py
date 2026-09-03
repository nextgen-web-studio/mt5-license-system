import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def check_db():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, vps_id FROM orders WHERE id = 20"))
        print(res.fetchall())

asyncio.run(check_db())
