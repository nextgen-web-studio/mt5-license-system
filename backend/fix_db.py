import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def fix_db():
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE orders SET vps_id = 4 WHERE id = 16"))
        await db.execute(text("UPDATE orders SET vps_id = 7 WHERE id = 14"))
        await db.execute(text("UPDATE orders SET vps_id = 7 WHERE id = 12"))
        await db.execute(text("UPDATE orders SET vps_id = 7 WHERE id = 11"))
        await db.commit()
        print("Fixed database!")

asyncio.run(fix_db())
