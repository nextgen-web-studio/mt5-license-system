import os
import subprocess
import asyncio
from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.models import CompileJob, License
import re
import httpx

async def local_wine_compiler(job_id: int):
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

        # 1. Prepare Paths
        base_dir = Path("/app")
        mq5_template = base_dir / "compiler" / "templates" / "bot.mq5"
        temp_dir = base_dir / "temp_builds"
        temp_dir.mkdir(exist_ok=True)
        
        build_mq5 = temp_dir / f"bot_{job_id}.mq5"
        build_ex5 = temp_dir / f"bot_{job_id}.ex5"
        log_file = temp_dir / f"bot_{job_id}.log"

        # 2. Inject Code
        with open(mq5_template, 'r', encoding='utf-8') as f:
            code = f.read()

        code = re.sub(r'int\s+ALLOWED_MT5_ID\s*=\s*\d+;', f'int ALLOWED_MT5_ID = {mt5_id};', code)
        code = re.sub(r'datetime\s+LICENSE_EXPIRY\s*=\s*D\'[^\']*\';', f'datetime LICENSE_EXPIRY = D\'{expiry}\';', code)

        with open(build_mq5, 'w', encoding='utf-8') as f:
            f.write(code)

        # 3. Compile with WINE and Xvfb
        metaeditor = base_dir / "metaeditor64.exe"
        
        # Suppress Mono/Gecko installation popups and WINE debug logs
        env = os.environ.copy()
        env["WINEDLLOVERRIDES"] = "mscoree,mshtml="
        env["WINEDEBUG"] = "-all"

        cmd = f'xvfb-run -a wine "{metaeditor}" /compile:"{build_mq5}" /log:"{log_file}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Add a 60 second timeout so it never hangs forever again
        try:
            await asyncio.wait_for(process.communicate(), timeout=300.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            print("WINE compilation timed out and was killed.")

        # 4. Check if EX5 exists and upload it internally to trigger delivery
        if build_ex5.exists():
            # Always call ourselves on localhost - the compiler runs on the same server as the API
            port = os.getenv("PORT", "8000")
            api_url = f"http://localhost:{port}/api/v1"
            worker_key = os.getenv("INFINITY_WORKER_API_KEY", "")
            
            with open(build_ex5, 'rb') as f:
                files = {'file': (f"InfinityTrader_{mt5_id}.ex5", f, 'application/octet-stream')}
                headers = {'infinity-worker-api-key': worker_key}
                async with httpx.AsyncClient(verify=False) as client:
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
                    job.error_message = "WINE Compilation Failed - EX5 missing"
                    await db.commit()

    except Exception as e:
        print(f"Local compile error: {e}")



