import asyncio
import os
import sys

sys.path.append(os.path.dirname(__file__))

from app.db.database import get_db, AsyncSessionLocal
from sqlalchemy import text

async def alter_table():
    print("Altering table...")
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(text("ALTER TABLE orders ADD COLUMN mt5_id VARCHAR;"))
            await db.commit()
            print("Successfully added mt5_id to orders table.")
        except Exception as e:
            print(f"Error (maybe already exists?): {e}")

if __name__ == "__main__":
    asyncio.run(alter_table())
