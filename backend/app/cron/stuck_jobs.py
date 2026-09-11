import asyncio
import os
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models import CompileJob, License, Order

async def check_and_reset_stuck_jobs():
    """
    Finds jobs that have been stuck in 'processing' for > 5 minutes.
    If the worker crashed silently, this will catch it, mark the job as 'failed',
    and notify the admin via Telegram so they can retry.
    """
    try:
        async with AsyncSessionLocal() as db:
            # 5 minutes ago
            timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            # Find stuck jobs
            result = await db.execute(
                select(CompileJob).where(
                    CompileJob.status == "processing",
                    CompileJob.started_at < timeout_threshold
                )
            )
            stuck_jobs = result.scalars().all()
            
            for job in stuck_jobs:
                job.status = "failed"
                job.error_message = "Job timed out and worker crashed. Please check the uploaded MQ5 template and retry."
                job.completed_at = datetime.now(timezone.utc)
                
                # Fetch order ID for notification
                order_id = "Unknown"
                lic_res = await db.execute(select(License).filter(License.id == job.license_id))
                lic = lic_res.scalar_one_or_none()
                if lic:
                    ord_res = await db.execute(select(Order).filter(Order.id == lic.order_id))
                    ord_obj = ord_res.scalar_one_or_none()
                    if ord_obj:
                        order_id = ord_obj.id
                
                print(f"Sweeper caught stuck job #{job.id} for Order #{order_id}")
                
                # Notify Telegram
                bot_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-6gf3.onrender.com")
                bot_webhook_url = bot_webhook_url.replace("/internal/delivery", "").replace("/internal/compile-started", "").replace("/internal/order-approved", "").replace("/bot", "").rstrip("/")
                bot_webhook_url += "/internal/compile-failed"
                try:
                    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                        await client.post(bot_webhook_url, json={
                            "job_id": job.id,
                            "order_id": order_id,
                            "error_message": job.error_message
                        })
                except Exception as e:
                    print(f"Sweeper failed to notify Telegram: {e}")
            
            if stuck_jobs:
                await db.commit()
                
    except Exception as e:
        print(f"Error in stuck jobs sweeper: {e}")
