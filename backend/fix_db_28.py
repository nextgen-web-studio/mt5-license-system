import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def fix_db():
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE orders SET status = 'pending_admin_approval' WHERE id = 28"))
        await db.commit()
        print("Fixed database!")

asyncio.run(fix_db())
