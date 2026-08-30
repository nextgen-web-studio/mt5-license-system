import os
import subprocess
import asyncio
from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.models import CompileJob, License, EaTemplate
import re
import httpx

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
                        return
                else:
                    original_code = active_template.source_code

            # 1. Prepare Paths
            base_dir = Path("/app")
            temp_dir = base_dir / "temp_builds"
            temp_dir.mkdir(exist_ok=True)
            
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
            env = os.environ.copy()
            # Try multiple possible paths where MetaEditor might be
            metaeditor = None
            for candidate in ["/app/metaeditor64.exe", "/app/metaeditor/metaeditor64.exe", "/app/MetaEditor64.exe"]:
                if Path(candidate).exists():
                    metaeditor = candidate
                    break
            if not metaeditor:
                async with AsyncSessionLocal() as db2:
                    r = await db2.execute(select(CompileJob).filter(CompileJob.id == job_id))
                    j = r.scalar_one_or_none()
                    if j:
                        j.status = "failed"
                        j.error_message = "MetaEditor64.exe not found. Check Dockerfile setup."
                        await db2.commit()
                return
            
            # Add these specific Wine flags to prevent headless crashing
            env["WINEDLLOVERRIDES"] = "mscoree,mshtml="
            env["WINEDEBUG"] = "-all"

            cmd = f'xvfb-run -a wine "{metaeditor}" /compile:"{build_mq5}" /log:"{log_file}"'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            # 4. Check results and Upload to central server
            if build_ex5.exists():
                api_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
                admin_token = os.getenv("ADMIN_TOKEN", "supersecretadmin123")
                
                headers = {"Authorization": f"Bearer {admin_token}"}
                
                async with httpx.AsyncClient() as client:
                    with open(build_ex5, 'rb') as f:
                        files = {'file': (f'bot_{job_id}.ex5', f, 'application/octet-stream')}
                        await client.post(f"{api_url}/jobs/{job_id}/upload", headers=headers, files=files, timeout=300.0)
                
                # Cleanup
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
                            with open(log_file, 'r', encoding='utf-16') as lf:
                                log_content = lf.read()
                        job.error_message = log_content[:1000]
                        await db.commit()

        except Exception as e:
            import traceback
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e) + "\\n" + traceback.format_exc()
                    await db.commit()
