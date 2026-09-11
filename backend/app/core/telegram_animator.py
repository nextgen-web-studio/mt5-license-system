import os
import httpx
import asyncio
import logging
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.models import CompileJob, License, Order
from datetime import datetime, timezone

async def animate_compiling(bot_token: str, chat_id: str, license_id: int, order_id: int = None):
    if not bot_token:
        return
        
    # Attempt to update the original Order Summary message to "Approved"
    if order_id:
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                res = await db.execute(text("SELECT message_id FROM bot_message_map WHERE key = :key"), {"key": f"CUST_ORD_{order_id}"})
                row = res.fetchone()
                if row and row[0]:
                    msg_id = row[0]
                    # Fetch order details to recreate the message with updated status
                    order_res = await db.execute(select(Order).filter(Order.id == order_id))
                    order_obj = order_res.scalar_one_or_none()
                    
                    if order_obj:
                        from app.models import Product, User
                        prod_res = await db.execute(select(Product).filter(Product.id == order_obj.product_id))
                        prod = prod_res.scalar_one_or_none()
                        
                        user_res = await db.execute(select(User).filter(User.id == order_obj.user_id))
                        user = user_res.scalar_one_or_none()
                        
                        # Simplified approved receipt update
                        now_str = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
                        updated_msg = (
                            f"📋 *ORDER SUMMARY*\n\n"
                            f"Order ID: #ORD-{order_id}\n"
                            f"👤 Name: {user.name or user.username or 'Unknown'}\n"
                            f"🔑 MT5 ID: `{order_obj.mt5_id}`\n"
                            f"📦 Plan: {prod.name if prod else 'Unknown'}\n\n"
                            f"Status: ✅ *Approved* ({now_str})\n\n"
                            f"_Your order has been approved by the admin._"
                        )
                        async with httpx.AsyncClient(verify=False) as client:
                            await client.post(
                                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                                json={
                                    "chat_id": chat_id,
                                    "message_id": msg_id,
                                    "text": updated_msg,
                                    "parse_mode": "Markdown"
                                }
                            )
        except Exception as e:
            logging.error(f"Failed to update original order summary: {e}")

    # Start the compiling progress bar
    initial_msg = (
        f"⚙️ *Generating your EA File...*\n\n"
        f"`[----------] 0%`\n\n"
        f"Please wait while we securely compile your file..."
    )
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": initial_msg, "parse_mode": "Markdown"}
            )
            if resp.status_code != 200:
                return
            data = resp.json()
            message_id = data['result']['message_id']
            
            # Use localhost to fetch queue position - same server
            import os as _os
            _port = _os.environ.get("PORT", "10000")
            base_url = f"http://127.0.0.1:{_port}/api/v1"
            
            # Fake progress mapping
            progress_steps = [10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95]
            
            for i in range(150):  # 150 * 2s = 300 seconds
                await asyncio.sleep(2)
                
                # Check specific queue position every 4 seconds
                queue_msg = "Your EA file is being built right now."
                if i % 2 == 0:
                    try:
                        job_resp = await client.get(f"{base_url}/jobs/queue-position/{license_id}")
                        if job_resp.status_code == 200:
                            jdata = job_resp.json()
                            pos = jdata.get("position", 0)
                            status = jdata.get("status", "completed")
                            
                            if pos > 1:
                                queue_msg = f"You are in queue position: #{pos}"
                            elif pos == 1 and status == "processing":
                                queue_msg = "Your EA is being compiled right now!"
                            elif pos == 1 and status == "pending":
                                queue_msg = "You are next in line!"
                            elif pos == 0:
                                # Job done, stop animating
                                break
                    except Exception:
                        pass
                
                pct = progress_steps[min(i, len(progress_steps)-1)]
                filled = int(pct / 10)
                bar = "=" * filled + "-" * (10 - filled)
                
                text = f"⚙️ *Generating your EA File...*\n\n`[{bar}] {pct}%`\n\n_{queue_msg}_"
                
                try:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/editMessageText",
                        json={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "text": text,
                            "parse_mode": "Markdown"
                        }
                    )
                except Exception:
                    pass

            # Once the loop is finished (job completed or timed out)
            # Edit the progress bar to 100% complete instead of deleting it
            try:
                final_text = (
                    f"✅ *Generation Complete!*\n\n"
                    f"`[==========] 100%`\n\n"
                    f"_Your EA file is ready below._"
                )
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/editMessageText",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": final_text,
                        "parse_mode": "Markdown"
                    }
                )
            except Exception:
                pass

    except Exception as e:
        logging.error(f"Failed to animate compile message: {e}")
