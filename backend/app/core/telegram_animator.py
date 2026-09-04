import os
import httpx
import asyncio
import logging

async def animate_compiling(bot_token: str, chat_id: str):
    if not bot_token:
        return
        
    initial_msg = (
        f"⏳ *Compiling your EA...*\n\n"
        f"Your EA file is being built right now.\n"
        f"The file will be sent here automatically once ready.\n\n"
        f"_Usually takes 2-5 minutes. Please wait._"
    )
    try:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": initial_msg, "parse_mode": "Markdown"}
            )
            if resp.status_code == 200:
                data = resp.json()
                message_id = data['result']['message_id']
                
                ring_frames = ["⏱️", "⏳", "⌛"]
                base_tail = "\n\nYour EA file is being built right now.\nThe file will be sent here automatically once ready.\n\n_Usually takes 2-5 minutes. Please wait._"
                
                for i in range(15):
                    await asyncio.sleep(4)
                    
                    queue_msg = "\n\n🔨 Your EA is being compiled right now!"
                    ring = ring_frames[i % len(ring_frames)]
                    text = f"{ring}⚙️ *Compiling your EA...*" + queue_msg + base_tail
                    
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/editMessageText",
                        json={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "text": text,
                            "parse_mode": "Markdown"
                        }
                    )
    except Exception as e:
        logging.error(f"Failed to animate compile message: {e}")
