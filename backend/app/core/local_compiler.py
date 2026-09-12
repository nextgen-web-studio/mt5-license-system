import os
import subprocess
import asyncio
from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.models import CompileJob, License, EaTemplate, Order
import re
import httpx
from datetime import datetime

# Global lock to prevent WINE from running concurrently and crashing the server (OOM)
compile_lock = asyncio.Lock()

async def local_wine_compiler(job_id: int):
    # Acquire the lock to ensure only one WINE compilation runs at a time
    async with compile_lock:
        # This runs in the background on Render using WINE
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
                job = result.scalar_one_or_none()
                if not job: return

                job.status = "processing"
                await db.commit()

                lic_result = await db.execute(select(License).filter(License.id == job.license_id))
                lic = lic_result.scalar_one_or_none()

                mt5_id = lic.mt5_id
                expiry = lic.expiry_date.strftime("%Y.%m.%d") if lic.expiry_date else "2099.01.01"
                
                # Fetch the active EA template from the database!
                template_result = await db.execute(select(EaTemplate).filter(EaTemplate.is_active == True))
                active_template = template_result.scalar_one_or_none()
                
                if not active_template or not active_template.source_code:
                    # Fallback to local file template
                    fallback = Path("/app/compiler/templates/bot.mq5")
                    if fallback.exists():
                        original_code = fallback.read_text(encoding="utf-8")
                    else:
                        job.status = "failed"
                        job.error_message = "No active EA template found in database and no fallback template found."
                        await db.commit()
                        await _notify_telegram_fail(db, job)
                        return
                else:
                    original_code = active_template.source_code

            # 1. Prepare Paths
            base_dir = Path.cwd()
            if not base_dir.name == "backend" and (base_dir / "backend").exists():
                base_dir = base_dir / "backend"
                
            temp_dir = base_dir / "temp_builds"
            # create parent dirs if needed
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            build_mq5 = temp_dir / f"bot_{job_id}.mq5"
            build_ex5 = temp_dir / f"bot_{job_id}.ex5"
            log_file = temp_dir / f"bot_{job_id}.log"

            # 2. Inject Code
            code = original_code
            code = re.sub(r'int\s+ALLOWED_MT5_ID\s*=\s*\d+;', f'int ALLOWED_MT5_ID = {mt5_id};', code)
            code = re.sub(r'datetime\s+LICENSE_EXPIRY\s*=\s*D\'[^\']*\';', f'datetime LICENSE_EXPIRY = D\'{expiry}\';', code)

            with open(build_mq5, 'w', encoding='utf-8') as f:
                f.write(code)

            # 3. Compile with WINE and Xvfb
            import shutil
            if not shutil.which("wine"):
                async with AsyncSessionLocal() as db2:
                    r = await db2.execute(select(CompileJob).filter(CompileJob.id == job_id))
                    j = r.scalar_one_or_none()
                    if j:
                        j.status = "failed"
                        j.error_message = "Wine is not installed on this server. You MUST deploy this backend using the Docker setup, not as a Native Web Service!"
                        await db2.commit()
                return

            env = os.environ.copy()
            # Try multiple possible paths where MetaEditor might be
            metaeditor = None
            for candidate in [
                base_dir / "metaeditor64.exe", 
                base_dir / "metaeditor" / "metaeditor64.exe",
                base_dir / "MetaEditor64.exe",
                "/app/metaeditor64.exe"
            ]:
                if Path(candidate).exists():
                    metaeditor = str(candidate)
                    break
            if not metaeditor:
                async with AsyncSessionLocal() as db:
                    r = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
                    job = r.scalar_one_or_none()
                    if job:
                        job.status = "failed"
                        job.error_message = "MetaEditor64.exe not found. Check Dockerfile setup."
                        await db.commit()
                        await _notify_telegram_fail(db, job)
                return
            
            # Add these specific Wine flags to prevent headless crashing
            env["WINEDLLOVERRIDES"] = "mscoree,mshtml="
            env["WINEDEBUG"] = "-all"

            cmd = f'xvfb-run -a wine "{metaeditor}" /compile:"{build_mq5}" /log:"{log_file}"'
            print(f"[COMPILER] Running: {cmd}", flush=True)

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            print(f"[COMPILER] WINE process started, PID={process.pid}, waiting up to 300s...", flush=True)
            timed_out = False
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)
            except asyncio.TimeoutError:
                print("[COMPILER] WINE process TIMED OUT after 300s! Killing and retrying once...", flush=True)
                timed_out = True
                try:
                    process.kill()
                except Exception:
                    pass
                stdout, stderr = b"", b""

            # Auto-retry once on timeout (Wine cold-start can be slow first time)
            if timed_out:
                print("[COMPILER] Auto-retry attempt after timeout...", flush=True)
                process2 = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
                try:
                    stdout, stderr = await asyncio.wait_for(process2.communicate(), timeout=300.0)
                    timed_out = False
                    print(f"[COMPILER] Retry succeeded. Return code: {process2.returncode}", flush=True)
                except asyncio.TimeoutError:
                    print("[COMPILER] Retry also TIMED OUT. Marking as failed.", flush=True)
                    try:
                        process2.kill()
                    except Exception:
                        pass
                    stdout, stderr = b"", b"WINE process timed out twice (600s total)"

            print(f"[COMPILER] WINE finished. Return code: {process.returncode}", flush=True)
            if stderr:
                print(f"[COMPILER] STDERR: {stderr.decode('utf-8', errors='replace')[:500]}", flush=True)
            
            # 4. Check results and Upload directly to Supabase (no HTTP self-call!)
            if build_ex5.exists():
                content = build_ex5.read_bytes()
                
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SECRET_KEY")
                
                if supabase_url and supabase_key:
                    from supabase import create_client
                    supabase = create_client(supabase_url, supabase_key)
                    bucket_name = "licenses"
                    file_path = f"{job_id}/{job_id}/bot.ex5"
                    
                    try:
                        supabase.storage.create_bucket(bucket_name, {"public": True})
                    except Exception:
                        pass
                    
                    supabase.storage.from_(bucket_name).upload(file_path, content, file_options={"upsert": "true"})
                    
                    # Update DB directly
                    async with AsyncSessionLocal() as db2:
                        r = await db2.execute(select(CompileJob).filter(CompileJob.id == job_id))
                        j = r.scalar_one_or_none()
                        if j:
                            j.status = "completed"
                            j.completed_at = datetime.utcnow()
                        
                        lic_r = await db2.execute(select(License).filter(License.id == j.license_id if j else -1))
                        lic = lic_r.scalar_one_or_none()
                        if lic:
                            lic.generated_filename = file_path
                            lic.status = "active"
                            ord_r = await db2.execute(select(Order).filter(Order.id == lic.order_id))
                            ord_obj = ord_r.scalar_one_or_none()
                            if ord_obj:
                                ord_obj.status = "delivered"
                        
                        await db2.commit()
                        
                        # Notify the Telegram Bot to deliver the file!
                        bot_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-k6h3.onrender.com")
                        bot_webhook_url = bot_webhook_url.replace("/internal/delivery", "").replace("/internal/compile-started", "").replace("/internal/order-approved", "").replace("/bot", "").rstrip("/")
                        bot_webhook_url += "/internal/delivery" 
                        try:
                            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                                await client.post(bot_webhook_url, json={"license_id": j.license_id})
                        except Exception as e:
                            print(f"Failed to notify Telegram bot for delivery: {e}")
                else:
                    # No Supabase — mark completed anyway (file delivery handled separately)
                    async with AsyncSessionLocal() as db2:
                        r = await db2.execute(select(CompileJob).filter(CompileJob.id == job_id))
                        j = r.scalar_one_or_none()
                        if j:
                            j.status = "completed"
                            j.completed_at = datetime.utcnow()
                        await db2.commit()
                
                # Cleanup temp files
                build_mq5.unlink(missing_ok=True)
                build_ex5.unlink(missing_ok=True)
                log_file.unlink(missing_ok=True)
            else:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
                    job = result.scalar_one_or_none()
                    if job:
                        job.status = "failed"
                        log_content = "Unknown compilation error"
                        if log_file.exists():
                            # Try utf-16 first (MetaEditor default), fallback to utf-8
                            for enc in ['utf-16', 'utf-8', 'latin-1']:
                                try:
                                    with open(log_file, 'r', encoding=enc) as lf:
                                        log_content = lf.read()
                                    break
                                except Exception:
                                    continue
                        # Also append wine stderr for maximum debug info
                        wine_err = stderr.decode('utf-8', errors='replace') if stderr else ""
                        if wine_err.strip():
                            log_content += f"\n\n--- WINE STDERR ---\n{wine_err[:500]}"
                        job.error_message = log_content[:2000]
                        await db.commit()
                        await _notify_telegram_fail(db, job)

        except Exception as e:
            import traceback
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e) + "\n" + traceback.format_exc()
                    await db.commit()
                    await _notify_telegram_fail(db, job)

async def _notify_telegram_fail(db, job):
    from app.models import License, Order, User
    import os, httpx
    from sqlalchemy import select
    
    order_id = "Unknown"
    telegram_id = None
    if job.license_id:
        lic_res = await db.execute(select(License).filter(License.id == job.license_id))
        lic = lic_res.scalar_one_or_none()
        if lic:
            ord_res = await db.execute(select(Order).filter(Order.id == lic.order_id))
            ord_obj = ord_res.scalar_one_or_none()
            if ord_obj:
                order_id = ord_obj.id
                
            user_res = await db.execute(select(User).filter(User.id == lic.user_id))
            user = user_res.scalar_one_or_none()
            if user:
                telegram_id = user.telegram_id
            elif lic.license_type == "trial":
                from app.models import TrialClaim
                claim_res = await db.execute(select(TrialClaim).filter(TrialClaim.license_id == lic.id))
                claim = claim_res.scalar_one_or_none()
                if claim:
                    telegram_id = claim.telegram_id

    bot_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-6gf3.onrender.com")
    bot_webhook_url = bot_webhook_url.replace("/internal/delivery", "").replace("/internal/compile-started", "").replace("/internal/order-approved", "").replace("/bot", "").rstrip("/")
    bot_webhook_url += "/internal/compile-failed"
    try:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            await client.post(bot_webhook_url, json={
                "job_id": job.id,
                "order_id": order_id,
                "telegram_id": telegram_id,
                "error_message": job.error_message
            })
    except Exception as e:
        print(f"Failed to notify Telegram bot of compile failure: {e}")
