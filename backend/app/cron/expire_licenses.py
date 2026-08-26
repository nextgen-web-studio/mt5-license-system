import asyncio
import os
import httpx
from datetime import datetime, timedelta
import sys

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import get_db, AsyncSessionLocal
from sqlalchemy.future import select
from sqlalchemy import delete
from app.models import License, User, Order, Payment, CompileJob

async def run_expiration_check():
    print(f"[{datetime.utcnow()}] Running license expiration check...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not found, skipping notifications.")
        return

    async with AsyncSessionLocal() as db:
        # Find active licenses
        result = await db.execute(select(License).filter(License.status == "active"))
        licenses = result.scalars().all()
        
        # 0. Stale Job Recovery
        now = datetime.utcnow()
        stale_threshold = now - timedelta(minutes=15)
        stale_jobs_result = await db.execute(
            select(CompileJob)
            .filter(CompileJob.status == "processing")
            .filter(CompileJob.started_at < stale_threshold)
        )
        stale_jobs = stale_jobs_result.scalars().all()
        recovered_count = 0
        for job in stale_jobs:
            if job.attempt_count >= 3:
                job.status = "failed"
                job.error_message = "Max attempts reached after stale recovery"
            else:
                job.status = "pending"
                job.worker_id = None
                job.started_at = None
            recovered_count += 1
        
        if recovered_count > 0:
            await db.commit()
            print(f"[{datetime.utcnow()}] Recovered {recovered_count} stale compile jobs.")
        notified_count = 0
        expired_count = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            for lic in licenses:
                if not lic.expiry_date:
                    continue
                    
                expiry_unaware = lic.expiry_date.replace(tzinfo=None) if lic.expiry_date.tzinfo else lic.expiry_date
                days_expired = (now - expiry_unaware).days
                
                # If just expired (0 to 1 day)
                if 0 <= days_expired < 1:
                    # Get user
                    user_result = await db.execute(select(User).filter(User.id == lic.user_id))
                    user = user_result.scalar_one_or_none()
                    
                    if user and user.telegram_id:
                        msg = (
                            f"⚠️ *Subscription Finished!*\n\n"
                            f"Your EA License for MT5 ID `{lic.mt5_id}` has expired.\n"
                            f"Please renew your subscription within *5 days*.\n\n"
                            f"If there is no response, the license will be eligible for deletion."
                        )
                        try:
                            await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                            )
                            notified_count += 1
                        except Exception as e:
                            print(f"Failed to notify user {user.telegram_id}: {e}")
                            
                # If expired >= 5 days, completely delete data
                if days_expired >= 5:
                    order_id = lic.order_id
                    
                    # 1. Delete CompileJobs
                    await db.execute(delete(CompileJob).filter(CompileJob.license_id == lic.id))
                    
                    # 2. Delete License
                    await db.execute(delete(License).filter(License.id == lic.id))
                    
                    # 3. Delete Payment
                    if order_id:
                        await db.execute(delete(Payment).filter(Payment.order_id == order_id))
                        
                        # 4. Delete Order
                        await db.execute(delete(Order).filter(Order.id == order_id))
                        
                    expired_count += 1
                    
        if expired_count > 0:
            await db.commit()
            
        # ─── 5-day installment payment reminder ──────────────────────────────
        installment_orders_res = await db.execute(
            select(Order).filter(Order.installment_enabled == True, Order.installment_status != "completed")
        )
        installment_orders = installment_orders_res.scalars().all()
        
        async with httpx.AsyncClient(verify=False) as client:
            for order in installment_orders:
                if not order.next_due_date:
                    continue
                next_due = order.next_due_date.replace(tzinfo=None) if order.next_due_date.tzinfo else order.next_due_date
                days_left = (next_due - now).days

                # Only remind exactly when 5 days are left (fires within the 12h cron window)
                if days_left == 5 or days_left == 4:
                    user_res = await db.execute(select(User).filter(User.id == order.user_id))
                    user = user_res.scalar_one_or_none()
                    if user and user.telegram_id:
                        due_str = next_due.strftime('%d %B %Y')
                        msg = (
                            f"⏰ *INSTALLMENT PAYMENT REMINDER*\n\n"
                            f"Your next installment payment is due in *{days_left} days*.\n\n"
                            f"💰 Amount Due: ₹{order.installment_amount:,.0f}\n"
                            f"📅 Due Date: {due_str}\n\n"
                            f"⚠️ Please make your payment on time to avoid losing EA access.\n\n"
                            f"Contact your admin to pay and extend your license."
                        )
                        try:
                            await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                            )
                        except Exception as e:
                            print(f"Failed to send installment reminder: {e}")
                            
        print(f"[{datetime.utcnow()}] Done. Sent {notified_count} notifications. Marked {expired_count} as expired.")

if __name__ == "__main__":
    asyncio.run(run_expiration_check())
