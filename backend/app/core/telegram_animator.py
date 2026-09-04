import os
import httpx
import asyncio
import logging

async def animate_compiling(bot_token: str, chat_id: str, license_id: int):
    if not bot_token:
        return
        
    initial_msg = (
        f"⏳ *Compiling your EA...*\n\n"
        f"Your EA file is being built right now.\n"
        f"The file will be sent here automatically once ready.\n\n"
        f"_Usually takes 2-5 minutes. Please wait._"
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
            
            ring_frames = ["⏱️", "⏳", "⌛"]
            base_tail = (
                "\n\nYour EA file is being built right now.\n"
                "The file will be sent here automatically once ready.\n\n"
                "_Usually takes 2-5 minutes. Please wait._"
            )
            
            # Use localhost to fetch queue position - same server
            base_url = "http://127.0.0.1:10000/api/v1"
            
            for i in range(25):  # 25 * 4s = 100 seconds
                await asyncio.sleep(4)
                
                queue_msg = "\n\n🔨 *Your EA is being compiled right now!*"
                
                try:
                    job_resp = await client.get(f"{base_url}/jobs/queue-position/{license_id}")
                    if job_resp.status_code == 200:
                        jdata = job_resp.json()
                        pos = jdata.get("position", 0)
                        status = jdata.get("status", "completed")
                        
                        if pos > 1:
                            queue_msg = f"\n\n👥 *You are in queue position: #{pos}*\n_Your EA will start compiling when it's your turn._"
                        elif pos == 1 and status == "processing":
                            queue_msg = "\n\n🔨 *Your EA is being compiled right now!*"
                        elif pos == 1 and status == "pending":
                            queue_msg = "\n\n🚀 *You are next in line!*\n_Your EA will start compiling shortly._"
                        elif pos == 0:
                            # Job done, stop animating
                            break
                except Exception:
                    pass
                
                ring = ring_frames[i % len(ring_frames)]
                text = f"{ring}⚙️ *Compiling your EA...*" + queue_msg + base_tail
                
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

    except Exception as e:
        logging.error(f"Failed to animate compile message: {e}")
