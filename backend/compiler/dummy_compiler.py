import os
import json
import zipfile
import shutil
import httpx
import asyncio
from interfaces import CompilerInterface

class DummyCompiler(CompilerInterface):
    """
    Dummy compiler used for Linux/Render deployments where MetaEditor is not available.
    """

    async def compile(self, job, license_obj, order, user, storage_dir, telegram_token) -> bool:
        try:
            # Notify Telegram: Compiling EA
            async with httpx.AsyncClient(verify=False) as client:
                res1 = await client.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": user.telegram_id,
                        "text": "📦 *Compiling EA...* Your personalized EA is being generated.",
                        "parse_mode": "Markdown"
                    }
                )
                res1.raise_for_status()

            await asyncio.sleep(2) # Simulate compile time
            
            # Copy DummyEA.exe
            dummy_exe_path = os.path.join(os.path.dirname(__file__), "DummyEA.exe")
            target_exe_path = os.path.join(storage_dir, "InfinityTrader.exe")
            
            if os.path.exists(dummy_exe_path):
                shutil.copy(dummy_exe_path, target_exe_path)
            else:
                # If DummyEA doesn't exist, just create a text file to represent it
                with open(target_exe_path, "w") as f:
                    f.write("Dummy EA content")
            
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
            
            # Notify Telegram: Ready
            async with httpx.AsyncClient(verify=False) as client:
                with open(zip_path, "rb") as document:
                    res2 = await client.post(
                        f"https://api.telegram.org/bot{telegram_token}/sendDocument",
                        data={
                            "chat_id": user.telegram_id,
                            "caption": "✅ *Download Ready!* Here is your personalized EA package."
                        },
                        files={"document": ("InfinityTrader.zip", document)}
                    )
                    if res2.status_code != 200:
                        raise Exception(f"Telegram API Error: {res2.text}")
                    
            return True
        except Exception as e:
            print(f"DummyCompiler failed: {e}")
            return False
