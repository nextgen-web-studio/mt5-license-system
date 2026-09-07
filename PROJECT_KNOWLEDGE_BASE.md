# Project Knowledge Base (For AI Agents)

**Target Audience:** Future Antigravity AI Agents or Human Developers.
**Purpose:** This file contains the complete architectural memory, directory maps, environment variables, and quirks of the Infinity Trader MT5 License System. 

---

## 1. Directory Structure & Key Files

### ??? Frontend (Next.js 13+ App Router)
Path: /frontend
*   src/app/admin/: Admin dashboard pages (e.g., orders/page.tsx, licenses/page.tsx, ps/page.tsx). Aggressively polls backend.
*   src/lib/api.ts: Core Axios instance. Automatically injects Bearer <admin_token> from cookies. **Do not remove _t=Date.now() here** (critical for WebView cache busting).
*   src/components/: Reusable React components (modals, UI elements).

### ?? Backend (FastAPI + SQLAlchemy)
Path: /backend/app
*   main.py: Application entry point. Registers all /api/v1 routers.
*   pi/v1/endpoints/:
    *   dmin.py: General dashboard stats and high-level queries.
    *   orders.py: Order approval, rejection, and VPS provisioning logic.
    *   licenses.py: License management, broker change requests, and CSV exports.
    *   products.py: Product definitions and pricing.
    *   uth.py: JWT generation and admin password management.
*   core/:
    *   security.py: Password hashing and JWT encoding. **(Note: get_current_admin is currently missing from endpoint routers - see Security Debt section).**
    *   local_compiler.py: Contains local_wine_compiler, a background task that runs MT5 compilation via Wine and uploads to Supabase.
    *   	elegram_animator.py: Real-time "Compiling..." spinner sent to Telegram during EA build.
*   models/: SQLAlchemy ORM definitions (User, Order, License, VpsOrder, BrokerChangeRequest, etc.).
*   db/database.py: AsyncPG engine connection and get_db session generator.

### ?? Telegram Bot (python-telegram-bot)
Path: /telegram_bot
*   ot.py: The massive main bot file. Handles commands (/start, /orders), inline button clicks (pprove_, eject_), and hosts the dummy Webhook server (e.g., DummyHandler on port 8080) to receive pings from the Backend.
*   utils/api_client.py: The bot's HTTP client to talk to the FastAPI backend. It attempts to inject X-Admin-Key.

---

## 2. Environment Variables Reference

To successfully run and deploy this project, the following .env keys must be present in their respective environments:

### Backend .env
*   DATABASE_URL: PostgreSQL connection string (Supabase AsyncPG format: postgresql+asyncpg://...).
*   SECRET_KEY: Used in uth.py/security.py for signing JWT tokens.
*   TELEGRAM_BOT_TOKEN: Required for the backend to directly send compilation animations and rejection notices to users.
*   TELEGRAM_WEBHOOK_URL: The URL of the Telegram Bot's dummy server (e.g., https://.../internal/). Used by the backend to ping the bot when an order is approved on the web dashboard.
*   ADMIN_API_KEY: A secret key meant to authorize bot requests to the backend (currently unverified).

### Telegram Bot .env
*   TELEGRAM_BOT_TOKEN: The bot's core token from BotFather.
*   API_BASE_URL: URL pointing to the FastAPI backend (e.g., https://api.../api/v1).
*   ADMIN_CHAT_ID: The Telegram User ID of the primary admin (receives EA order requests).
*   VPS_ADMIN_CHAT_ID: The Telegram User ID of the VPS admin (receives VPS payment proofs).
*   ADMIN_API_KEY: Sent in the headers to the backend as X-Admin-Key.

### Frontend .env.local
*   NEXT_PUBLIC_API_URL: Points to the FastAPI backend for client-side API requests.

---

## 3. High-Level Workflows

### A. Order Approval & EA Delivery
1. User purchases EA.
2. Admin approves order either via **Web Dashboard** OR **Telegram Inline Button**.
3. **Backend (orders.py)**: Updates DB, triggers background compilation (local_wine_compiler).
4. **Backend Webhook**: Sends a POST /internal/order-approved webhook to the Telegram bot to dynamically clear the inline buttons from the admin's chat.
5. **Compilation**: Completes and triggers nimate_compiling, uploading to Supabase storage.
6. **Delivery**: The bot automatically sends the .ex5 document directly to the customer's Telegram chat.

---

## 4. CRITICAL Quirks & Known Issues (DO NOT BREAK THESE)

### Frontend: Mobile WebView Caching (pi.ts)
*   **DO NOT REMOVE CACHE-BUSTING:** In rontend/src/lib/api.ts, there is aggressive cache-busting (config.params._t = Date.now() and Cache-Control: no-cache). 
*   **Why:** The frontend is used inside mobile WebViews (iOS/Android) which have notoriously uncontrollable caching layers. If the cache-busting headers are removed, the WebView will permanently cache empty arrays or 401s, causing the app to freeze showing "No Orders".

### Backend: Missing Server-Side Authentication
*   **SECURITY DEBT:** While the Next.js frontend handles JWTs and the Telegram Bot passes an X-Admin-Key header, the **FastAPI backend currently lacks a dependency to enforce these keys on admin routes**.
*   If instructed to secure the backend, you must implement a dependency in security.py that validates *both* the Authorization: Bearer (from Next.js) and the X-Admin-Key (from the Bot), otherwise you will break the pipeline.

### Telegram Bot: Ephemeral State & Double Notifications
*   **dmin_messages.json is ephemeral:** The bot stores message IDs in a local JSON file. Because Render wipes local storage on every restart, the bot forgets old message IDs.
*   **Already Processed Handling:** If an admin clicks an old Telegram button that was already processed in the web dashboard, the backend returns HTTP 400. ot.py is specifically programmed to catch "already" or "not pending" in the error text and gracefully clear the buttons anyway.
*   **Double Messaging:** Be careful adding user notifications. Both the Backend (orders.py/licenses.py) and the Bot (ot.py) have logic to send Telegram messages. 

### Python Variable Scoping in Webhooks
*   **FastAPI Background Tasks:** When triggering a webhook from a backend endpoint (e.g., licenses.py), do not place import os below the nested webhook function definition. Always place imports globally or at the top of the nested function.

*End of Memory Dump. Proceed with confidence.*
