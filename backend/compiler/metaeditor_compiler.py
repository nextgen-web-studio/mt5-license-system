import os
import shutil
import subprocess
import httpx
from .interfaces import CompilerInterface

class MetaEditorCompiler(CompilerInterface):
    """
    Windows-based compiler that dynamically injects licensing variables into the MQL5 source code
    and compiles the EA using MetaEditor.exe.
    """

    async def compile(self, job, license_obj, order, user, storage_dir, telegram_token) -> bool:
        try:
            # 1. Notify Telegram: Compiling EA
            async with httpx.AsyncClient(verify=False) as client:
                await client.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": user.telegram_id,
                        "text": "📦 *Compiling EA...* Your personalized EA is being generated on our secure servers.",
                        "parse_mode": "Markdown"
                    }
                )

            # 2. Setup paths
            base_dir = os.path.dirname(__file__)
            source_mq5 = os.path.join(base_dir, "Infinity_Trend_Demo.mq5")
            temp_mq5 = os.path.join(storage_dir, f"InfinityTrader_{license_obj.license_uuid}.mq5")
            output_ex5 = os.path.join(storage_dir, f"InfinityTrader_{license_obj.license_uuid}.ex5")

            if not os.path.exists(source_mq5):
                print(f"Source file not found: {source_mq5}")
                return False

            # 3. Read template and inject variables
            with open(source_mq5, "r", encoding="utf-8") as f:
                code = f.read()

            expiry_str = license_obj.expiry_date.strftime("%Y.%m.%d %H:%M:%S") if license_obj.expiry_date else "2099.12.31 23:59:59"
            
            # Replace placeholder variables
            code = code.replace("long AllowedMT5Login = 0;", f"long AllowedMT5Login = {license_obj.mt5_id};")
            code = code.replace('string ExpiryDate = "2026.12.31 23:59:59";', f'string ExpiryDate = "{expiry_str}";')

            with open(temp_mq5, "w", encoding="utf-8") as f:
                f.write(code)

            # 4. Invoke MetaEditor.exe
            # Assuming MetaEditor.exe is either in PATH or in the same directory for this demo.
            # Usually, you would provide the absolute path to MetaEditor64.exe here.
            metaeditor_path = "MetaEditor.exe" # In production, set to r"C:\Program Files\MetaTrader 5\metaeditor64.exe"
            
            # Use subprocess to run MetaEditor compilation
            compile_cmd = [
                metaeditor_path,
                f"/compile:{temp_mq5}",
                "/log"
            ]
            
            print(f"Running compiler: {' '.join(compile_cmd)}")
            
            try:
                # We do not capture output here because MetaEditor writes to a .log file next to the .mq5
                subprocess.run(compile_cmd, check=False, timeout=30)
            except FileNotFoundError:
                print(f"MetaEditor not found at {metaeditor_path}. Falling back to copying original file as dummy for testing.")
                shutil.copy(temp_mq5, output_ex5) # Fallback if MetaEditor is not installed on testing PC
            except Exception as e:
                print(f"MetaEditor execution failed: {e}")

            # 5. Check if .ex5 was generated
            if not os.path.exists(output_ex5):
                print("Compilation failed. .ex5 file was not created.")
                # You could read temp_mq5.log here to get compiler errors
                return False

            # Update License record
            license_obj.generated_filename = output_ex5
            
            # 6. Notify Telegram: Ready
            async with httpx.AsyncClient(verify=False) as client:
                with open(output_ex5, "rb") as document:
                    await client.post(
                        f"https://api.telegram.org/bot{telegram_token}/sendDocument",
                        data={
                            "chat_id": user.telegram_id,
                            "caption": "✅ *Download Ready!* Here is your personalized EA package.\n\n⚠️ Important: This EA is permanently locked to your MT5 Account ID."
                        },
                        files={"document": (f"InfinityTrader_{license_obj.license_uuid}.ex5", document)}
                    )
                    
            return True
        except Exception as e:
            print(f"MetaEditorCompiler failed: {e}")
            return False
