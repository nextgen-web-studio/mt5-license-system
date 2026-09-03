import asyncio
import os
import sys

sys.path.append(os.path.dirname(__file__))

from app.db.database import get_db, AsyncSessionLocal
from sqlalchemy.future import select
from app.models import VpsOrder, Order, Product

async def fix_vps_durations():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(VpsOrder, Order, Product).join(Order, VpsOrder.order_id == Order.id).join(Product, Order.product_id == Product.id))
        rows = res.all()
        for vps, order, product in rows:
            if vps.duration == 1 and product.duration != 1:
                print(f"Fixing VPS {vps.id} duration to {product.duration}")
                vps.duration = product.duration
        await db.commit()
        print("Done fixing durations.")

if __name__ == "__main__":
    asyncio.run(fix_vps_durations())
