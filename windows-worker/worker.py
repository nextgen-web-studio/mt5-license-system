import os
import time
import requests
import subprocess
import shutil
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WORKER] %(message)s')

API_BASE_URL = os.getenv("API_BASE_URL", "https://infinity-trader-api.onrender.com/api/v1")
INFINITY_WORKER_API_KEY = os.getenv("INFINITY_WORKER_API_KEY")
WORKER_ID = os.getenv("WORKER_ID", "WINDOWS-PC-01")
METAEDITOR_PATH = os.getenv("METAEDITOR_PATH", r"C:\Program Files\MetaTrader 5\metaeditor64.exe")
POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "10"))
TEST_MODE = os.getenv("WORKER_TEST_MODE", "false").lower() == "true"

def compile_ea(mt5_id: str, job_id: int):
    # Prepare template
    template_path = os.path.join("templates", "bot.mq5")
    if not os.path.exists(template_path):
        raise Exception("Template file not found at templates/bot.mq5")
        
    temp_dir = f"temp_job_{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    source_file = os.path.join(temp_dir, f"bot_{job_id}.mq5")
    
    with open(template_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    # Inject MT5 ID
    code = code.replace("__MT5_LICENSE_ID__", mt5_id)
    
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(code)
        
    if TEST_MODE:
        logging.info("Test mode enabled, skipping MetaEditor.")
        output_file = os.path.join(temp_dir, f"bot_{job_id}.ex5")
        with open(output_file, "w") as f:
            f.write(f"DUMMY COMPILED EX5 FOR {mt5_id}")
        return output_file
        
    # Compile
    logging.info(f"Running MetaEditor for MT5 ID: {mt5_id}")
    cmd = [
        METAEDITOR_PATH,
        f"/compile:{source_file}",
        "/log"
    ]
    
    try:
        process = subprocess.run(cmd, capture_output=True, text=True)
        # Check if ex5 was generated
        output_file = os.path.join(temp_dir, f"bot_{job_id}.ex5")
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logging.info("Compilation successful.")
            return output_file
        else:
            log_file = os.path.join(temp_dir, f"bot_{job_id}.log")
            error_msg = f"Compilation failed. Return code: {process.returncode}"
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-16", errors="ignore") as lf:
                    error_msg += "\n" + lf.read()
            raise Exception(error_msg)
    except Exception as e:
        raise Exception(f"MetaEditor execution error: {e}")

def run_worker():
    logging.info(f"Started worker '{WORKER_ID}'")
    logging.info(f"API URL: {API_BASE_URL}")
    
    headers = {"infinity-worker-api-key": INFINITY_WORKER_API_KEY} if INFINITY_WORKER_API_KEY else {}
    
    while True:
        try:
            # Atomic claim
            resp = requests.post(f"{API_BASE_URL}/jobs/claim", json={"worker_id": WORKER_ID}, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    job = data["job"]
                    job_id = job["job_id"]
                    mt5_id = job["mt5_id"]
                    logging.info(f"Claimed job {job_id} for MT5 ID {mt5_id}")
                    
                    try:
                        ex5_path = compile_ea(mt5_id, job_id)
                        
                        # Upload
                        logging.info("Uploading result...")
                        with open(ex5_path, "rb") as f:
                            files = {"file": (os.path.basename(ex5_path), f, "application/octet-stream")}
                            upload_resp = requests.post(f"{API_BASE_URL}/jobs/{job_id}/upload", files=files, headers=headers)
                            
                        if upload_resp.status_code == 200:
                            logging.info(f"Job {job_id} completed successfully")
                        else:
                            logging.error(f"Failed to upload: {upload_resp.text}")
                    except Exception as e:
                        logging.error(f"Job {job_id} failed: {e}")
                        requests.post(f"{API_BASE_URL}/jobs/{job_id}/fail", json={
                            "worker_id": WORKER_ID,
                            "error_message": str(e)
                        }, headers=headers)
                    finally:
                        # Clean up temp files
                        temp_dir = f"temp_job_{job_id}"
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                            
            elif resp.status_code != 200 and resp.status_code != 404:
                logging.error(f"API Error {resp.status_code}: {resp.text}")
                
        except Exception as e:
            logging.error(f"Worker exception: {e}")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    if not INFINITY_WORKER_API_KEY:
        logging.warning("INFINITY_WORKER_API_KEY is not set. API calls may fail.")
    run_worker()
