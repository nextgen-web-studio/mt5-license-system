import os
import time
import requests
import subprocess
import shutil
import logging
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "worker.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

API_BASE_URL = os.getenv("API_BASE_URL", "https://infinity-trader-api.onrender.com/api/v1")
WORKER_API_KEY = os.getenv("WORKER_API_KEY")
WORKER_ID = os.getenv("WORKER_ID", "windows-worker-01")
METAEDITOR_PATH = os.getenv("METAEDITOR_PATH", r"C:\Program Files\MetaTrader 5\metaeditor64.exe")
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", os.path.join(os.path.dirname(__file__), "templates", "bot.mq5"))
WORK_DIR = os.getenv("WORK_DIR", os.path.join(os.path.dirname(__file__), "worker-temp"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))

def check_prerequisites():
    if not WORKER_API_KEY:
        raise Exception("WORKER_API_KEY is not set.")
    
    if not os.path.exists(METAEDITOR_PATH):
        raise Exception(f"MetaEditor not found at {METAEDITOR_PATH}")
        
    if not os.path.exists(TEMPLATE_PATH):
        raise Exception(f"Template not found at {TEMPLATE_PATH}")
        
    os.makedirs(WORK_DIR, exist_ok=True)
    logging.info("Prerequisites check passed.")

def is_valid_mt5_id(mt5_id: str) -> bool:
    # Must be alphanumeric, no weird paths
    return bool(re.match(r"^[A-Za-z0-9_-]+$", mt5_id))

def run_worker():
    logging.info(f"Worker '{WORKER_ID}' starting up...")
    
    try:
        check_prerequisites()
    except Exception as e:
        logging.error(f"Startup failed: {e}")
        return

    headers = {"infinity-worker-api-key": WORKER_API_KEY}
    
    # Test API
    try:
        resp = requests.get(f"{API_BASE_URL}/jobs/pending", headers=headers, timeout=10)
        resp.raise_for_status()
        logging.info("API connection successful.")
    except Exception as e:
        logging.error(f"Failed to connect to API: {e}")
        logging.info("Will keep retrying in loop...")
        
    while True:
        try:
            resp = requests.post(
                f"{API_BASE_URL}/jobs/claim", 
                json={"worker_id": WORKER_ID}, 
                headers=headers,
                timeout=15
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    job = data.get("job", {})
                    job_id = job.get("job_id")
                    mt5_id = job.get("mt5_id")
                    
                    if not job_id or not mt5_id:
                        logging.error(f"Invalid job payload: {job}")
                        continue
                        
                    logging.info(f"Job claimed: {job_id} for MT5 ID: {mt5_id}")
                    process_job(job_id, mt5_id, headers)
            elif resp.status_code != 200 and resp.status_code != 404:
                # 404 might just mean no pending jobs or incorrect route, but we assume empty return {"status": "empty"}
                logging.error(f"API Error {resp.status_code}: {resp.text}")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error while polling: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in poll loop: {e}")
            
        time.sleep(POLL_INTERVAL)

def process_job(job_id: int, mt5_id: str, headers: dict):
    job_dir = os.path.join(WORK_DIR, f"{job_id}")
    
    try:
        if not is_valid_mt5_id(mt5_id):
            raise Exception("Invalid MT5 ID format")

        os.makedirs(job_dir, exist_ok=True)
        source_file = os.path.join(job_dir, f"bot_{job_id}.mq5")
        
        # Read template safely
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            code = f.read()
            
        if "__MT5_LICENSE_ID__" not in code:
            raise Exception("Placeholder __MT5_LICENSE_ID__ not found in template.")
            
        code = code.replace("__MT5_LICENSE_ID__", mt5_id)
        
        with open(source_file, "w", encoding="utf-8") as f:
            f.write(code)
            
        logging.info(f"Temporary source created for job {job_id}")
        
        # Compile
        logging.info(f"MetaEditor compilation started for job {job_id}")
        cmd = [
            METAEDITOR_PATH,
            f"/compile:{source_file}",
            "/log"
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        output_file = os.path.join(job_dir, f"bot_{job_id}.ex5")
        log_file = os.path.join(job_dir, f"bot_{job_id}.log")
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logging.info(f"Compilation succeeded for job {job_id}")
            logging.info("EX5 validated")
            
            # Upload
            with open(output_file, "rb") as f:
                files = {"file": (f"InfinityTrader_{mt5_id}.ex5", f, "application/octet-stream")}
                upload_resp = requests.post(f"{API_BASE_URL}/jobs/{job_id}/upload", files=files, headers=headers, timeout=30)
                
            if upload_resp.status_code == 200:
                logging.info(f"Upload successful for job {job_id}")
                logging.info(f"Job completed: {job_id}")
            else:
                raise Exception(f"Failed to upload EX5. API returned {upload_resp.status_code}: {upload_resp.text}")
        else:
            error_msg = f"Compilation failed. Return code: {process.returncode}"
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-16", errors="ignore") as lf:
                    error_msg += "\n" + lf.read()
            raise Exception(error_msg)
            
    except Exception as e:
        logging.error(f"Job {job_id} failed: {e}")
        try:
            requests.post(f"{API_BASE_URL}/jobs/{job_id}/fail", json={
                "worker_id": WORKER_ID,
                "error_message": str(e)
            }, headers=headers, timeout=10)
        except Exception as api_err:
            logging.error(f"Failed to report job {job_id} failure to API: {api_err}")
    finally:
        # Cleanup
        try:
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
                logging.info(f"Cleaned up temporary directory for job {job_id}")
        except Exception as e:
            logging.warning(f"Failed to clean up {job_dir}: {e}")

if __name__ == "__main__":
    run_worker()
