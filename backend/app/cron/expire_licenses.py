import asyncio
import os
import httpx
from datetime import datetime, timedelta
import sys

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import get_db, SessionLocal
from sqlalchemy.future import select
from app.models import License, User

async def run_expiration_check():
    print(f"[{datetime.utcnow()}] Running license expiration check...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not found, skipping notifications.")
        return

    async with SessionLocal() as db:
        # Find active licenses
        result = await db.execute(select(License).filter(License.status == "active"))
        licenses = result.scalars().all()
        
        now = datetime.utcnow()
        notified_count = 0
        expired_count = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            for lic in licenses:
                if not lic.expiry_date:
                    continue
                    
                days_expired = (now - lic.expiry_date).days
                
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
                            
                # If expired > 5 days, mark status as expired (optional, as frontend will check date anyway)
                if days_expired >= 5 and lic.status == "active":
                    lic.status = "expired"
                    expired_count += 1
                    
        if expired_count > 0:
            await db.commit()
            
        print(f"[{datetime.utcnow()}] Done. Sent {notified_count} notifications. Marked {expired_count} as expired.")

if __name__ == "__main__":
    asyncio.run(run_expiration_check())
