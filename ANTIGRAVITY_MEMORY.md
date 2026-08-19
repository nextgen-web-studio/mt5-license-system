# ANTIGRAVITY MEMORY FILE: MT5 License System

*Dear future Antigravity instance (or other AI assistant): Read this document first to fully understand the context, architecture, and quirks of this project before making any code changes.*

## 1. Project Overview
This is a licensing and delivery system for MetaTrader 5 (MT5) Expert Advisors (EAs). 
- **Frontend:** Next.js (Admin Dashboard)
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (Hosted on Supabase, using asyncpg & SQLAlchemy)
- **Delivery:** A Python Telegram Bot that sends compiled `.ex5` files directly to customers.

## 2. The Unique Architecture (Two Servers)
This project requires a split architecture because MetaTrader 5 cannot run on Linux.
- **Server A (Linux):** Hosts the Next.js Frontend, the FastAPI Backend, and the Telegram Bot. This handles all web traffic and database queries 24/7.
- **Server B (Windows):** A dedicated Windows Virtual Machine. This runs a Python worker script (`windows-worker/worker.py`) that constantly polls Server A for new compiling jobs. It requires MT5's `metaeditor.exe` to physically compile the EAs.

## 3. How the .mq5 to .ex5 Compilation Works
When the Admin uploads an `.mq5` EA template via the dashboard, the backend extracts the raw text source code and saves it permanently inside the PostgreSQL database (in the `ea_versions` table, column `source_code`). 
1. When a user buys a license, Server A generates a pending job.
2. Server B (Windows) claims the job, downloads the raw code, and creates a temporary `.mq5` file.
3. Server B runs `metaeditor.exe` to compile it into `.ex5`.
4. Server B uploads the `.ex5` back to Server A.
5. Server A triggers the Telegram Bot (`/internal/delivery` webhook) to send the file to the customer.

## 4. The Azure Auto-Wake Feature (app/core/azure_vm.py)
To save money, the project currently uses Azure credentials in the backend `.env` to automatically boot up Server B (the Windows VM) only when a job is ready. 
- **Important for Migration:** If this project moves to a new cloud (like AWS), `azure_vm.py` must either be rewritten to use the new cloud's SDK, OR the Azure variables can be left completely blank in the `.env` (the code is programmed to safely ignore them and assume Server B is running 24/7).

## 5. Master Deployment Prompts
If the user is deploying this repo to a new cloud platform, use the following instructions to set up the environments:

**For Server A (Linux):**
- Create `.env` files for `frontend`, `backend`, and `telegram_bot`.
- Run `npm install` & `npm run build` for frontend.
- Create a Python venv and install `requirements.txt` for backend/bot.
- Use PM2 (`ecosystem.config.js`) to run Next.js (port 3000), Uvicorn (port 8000), and the Telegram Bot concurrently.
- Ensure the FastAPI CORS `allow_origins` accepts the new frontend IP.

**For Server B (Windows):**
- Setup a Python venv in `windows-worker/` and install `requests`, `httpx`, `python-dotenv`.
- Create a `.env` setting `API_BASE_URL` to Server A's IP, and `METAEDITOR_PATH` to the local MT5 installation.
- Create a `start_worker.bat` to run `worker.py` in an infinite loop, and add it to the Windows Task Scheduler to run on boot.
