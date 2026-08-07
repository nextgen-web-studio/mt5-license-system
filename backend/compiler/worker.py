import asyncio
import os
import json
import zipfile
import shutil
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from app.models import CompileJob, License, Order, User
import httpx

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def process_job(db: AsyncSession, job: CompileJob):
    # Fetch license, order, user
    res = await db.execute(select(License).filter(License.id == job.license_id))
    license_obj = res.scalar_one()
    
    res = await db.execute(select(Order).filter(Order.id == license_obj.order_id))
    order = res.scalar_one()
    
    res = await db.execute(select(User).filter(User.id == order.user_id))
    user = res.scalar_one()

    # Create workspace
    storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "licenses", str(license_obj.id))
    os.makedirs(storage_dir, exist_ok=True)
    
    # Notify Telegram: Compiling EA
    async with httpx.AsyncClient(verify=False) as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": user.telegram_id,
                "text": "📦 *Compiling EA...* Your personalized EA is being generated.",
                "parse_mode": "Markdown"
            }
        )

    await asyncio.sleep(2) # Simulate compile time
    
    try:
        # Copy DummyEA.exe
        dummy_exe_path = os.path.join(os.path.dirname(__file__), "DummyEA.exe")
        target_exe_path = os.path.join(storage_dir, "InfinityTrader.exe")
        shutil.copy(dummy_exe_path, target_exe_path)
        
        # Write License.json
        license_data = {
            "license_key": license_obj.license_uuid,
            "mt5_id": license_obj.mt5_id,
            "expiry_date": license_obj.expiry_date.isoformat() if license_obj.expiry_date else None,
            "status": "active"
        }
        with open(os.path.join(storage_dir, "license.json"), "w") as f:
            json.dump(license_data, f, indent=4)
            
        # Write README.txt
        with open(os.path.join(storage_dir, "README.txt"), "w") as f:
            f.write("Infinity Trader EA\n\n1. Copy InfinityTrader.exe to your MT5 Experts folder.\n2. Ensure your MT5 ID matches the one registered.\n")
            
        # Create ZIP
        zip_path = os.path.join(os.path.dirname(storage_dir), f"InfinityTrader_{license_obj.license_uuid}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(target_exe_path, arcname="InfinityTrader.exe")
            zipf.write(os.path.join(storage_dir, "license.json"), arcname="license.json")
            zipf.write(os.path.join(storage_dir, "README.txt"), arcname="README.txt")
            
        # Update License
        license_obj.generated_filename = zip_path
        
        # Update Job & Order
        job.status = "completed"
        order.status = "ready"
        await db.commit()
        
        # Notify Telegram: Ready
        async with httpx.AsyncClient(verify=False) as client:
            with open(zip_path, "rb") as document:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
                    data={
                        "chat_id": user.telegram_id,
                        "caption": "✅ *Download Ready!* Here is your personalized EA package."
                    },
                    files={"document": ("InfinityTrader.zip", document)}
                )
                
    except Exception as e:
        print(f"Failed to compile job {job.id}: {e}")
        job.status = "failed"
        await db.commit()

async def main():
    print("Starting Compiler Worker...")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    while True:
        async with async_session() as db:
            result = await db.execute(select(CompileJob).filter(CompileJob.status == "pending"))
            job = result.scalars().first()
            
            if job:
                print(f"Picked up job {job.id}")
                job.status = "processing"
                await db.commit()
                await process_job(db, job)
            else:
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
