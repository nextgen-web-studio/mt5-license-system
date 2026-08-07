import asyncio
import os
import json
import zipfile
import shutil
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Dummy web server started on port {port}")

from app.db.database import engine
from app.models import CompileJob, License, Order, User
import httpx

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def process_job(db: AsyncSession, job: CompileJob):
    try:
        # Fetch license, order, user
        res = await db.execute(select(License).filter(License.id == job.license_id))
        license_obj = res.scalar_one()
        
        res = await db.execute(select(Order).filter(Order.id == license_obj.order_id))
        order = res.scalar_one()
        
        res = await db.execute(select(User).filter(User.id == order.user_id))
        user = res.scalar_one()

        # Create workspace
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "licenses", str(license_obj.id))
        os.makedirs(storage_dir, exist_ok=True)
        
        # Initialize correct compiler based on OS
        if os.name == 'nt':
            from .metaeditor_compiler import MetaEditorCompiler
            compiler = MetaEditorCompiler()
        else:
            from .dummy_compiler import DummyCompiler
            compiler = DummyCompiler()
            
        success = await compiler.compile(job, license_obj, order, user, storage_dir, TELEGRAM_TOKEN)
        
        if success:
            job.status = "completed"
            job.logs = "Compilation completed successfully."
            order.status = "ready"
        else:
            job.status = "failed"
            job.logs = "Compiler script returned failure."
            
        await db.commit()
    except Exception as e:
        print(f"CRITICAL ERROR processing job {job.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        await db.rollback()
        job.status = "failed"
        job.logs = f"Crash in process_job: {str(e)}"
        await db.commit()

async def main():
    start_dummy_server()
    print("Starting Compiler Worker...")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    while True:
        async with async_session() as db:
            result = await db.execute(select(CompileJob).filter(CompileJob.status == "pending"))
            job = result.scalars().first()
            
            if job:
                print(f"Picked up job {job.id}")
                job.status = "processing"
                await db.commit()
                await process_job(db, job)
            else:
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
