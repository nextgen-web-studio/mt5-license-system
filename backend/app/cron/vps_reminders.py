import asyncio
import os
import httpx
from datetime import datetime, timedelta, timezone
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import get_db, AsyncSessionLocal
from sqlalchemy.future import select
from app.models import VpsOrder, User, Order

async def run_vps_reminders():
    logging.info(f"[{datetime.utcnow()}] Running VPS payment reminders check...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logging.warning("TELEGRAM_BOT_TOKEN not found, skipping VPS reminders.")
        return

    async with AsyncSessionLocal() as db:
        # Find active VPS orders with an expiry date
        result = await db.execute(select(VpsOrder).filter(VpsOrder.status == "provisioned"))
        vps_orders = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        notified_count = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            for vps in vps_orders:
                if not vps.expiry_date:
                    continue
                    
                expiry_dt = vps.expiry_date if vps.expiry_date.tzinfo else vps.expiry_date.replace(tzinfo=timezone.utc)
                days_left = (expiry_dt - now).days
                
                # Check if it's exactly 5 days left (or 4 days if we consider fraction of days depending on when cron runs)
                if days_left == 5 or days_left == 4:
                    user_res = await db.execute(select(User).filter(User.id == vps.user_id))
                    user = user_res.scalar_one_or_none()
                    
                    if user and user.telegram_id:
                        due_str = expiry_dt.strftime('%d %B %Y')
                        msg = (
                            f"🔔 *VPS RENEWAL REMINDER*\n\n"
                            f"Your VPS server is expiring in *{days_left} days*.\n\n"
                            f"🖥️ **Hostname:** `{vps.hostname or 'N/A'}`\n"
                            f"🌐 **IP:** `{vps.ip}`\n"
                            f"📅 **Due Date:** {due_str}\n\n"
                            f"⚠️ Please renew your VPS via the main menu to avoid downtime and data loss."
                        )
                        try:
                            await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                            )
                            notified_count += 1
                        except Exception as e:
                            logging.error(f"Failed to send VPS reminder to {user.telegram_id}: {e}")
                            
        logging.info(f"[{datetime.utcnow()}] VPS reminders done. Sent {notified_count} notifications.")

if __name__ == "__main__":
    asyncio.run(run_vps_reminders())
