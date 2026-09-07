# Project Knowledge Base (For AI Agents)

**Target Audience:** Future Antigravity AI Agents or Human Developers.
**Purpose:** This file contains the complete architectural memory, quirks, and context of the Infinity Trader MT5 License System. Read this before making architectural changes.

---

## 1. High-Level Architecture & Tech Stack
This project is an end-to-end licensing, delivery, and administration system for an MT5 Trading EA (Expert Advisor) and VPS provisioning. 

*   **Frontend**: Next.js 13+ (App Router), React, TailwindCSS, React Query (@tanstack/react-query), Axios. Packaged for mobile as a WebView/PWA.
*   **Backend**: FastAPI, SQLAlchemy (AsyncPG), PostgreSQL (hosted on Supabase).
*   **Telegram Bot**: python-telegram-bot, tightly coupled with the backend, uses httpx for internal API calls.
*   **Compiler Infrastructure**: Uses a local Wine-based compiler (pp.core.local_compiler.local_wine_compiler) running in background tasks to generate custom .ex5 files.
*   **Deployment**: Hosted on Render (Docker/Web Services). The Backend and Telegram Bot run in the same repository environment.

---

## 2. Core Workflows

### A. Order Approval & EA Delivery
1. User purchases EA.
2. Admin approves order either via **Web Dashboard** OR **Telegram Inline Button**.
3. **Backend (orders.py)**: Updates DB, triggers background compilation (local_wine_compiler).
4. **Backend Webhook**: Sends a POST /internal/order-approved webhook to the Telegram bot to dynamically clear the inline buttons from the admin's chat.
5. **Compilation**: Completes and triggers nimate_compiling, uploading to Supabase storage.
6. **Delivery**: The bot automatically sends the .ex5 document directly to the customer's Telegram chat.

### B. Broker Change Requests
1. User requests to change their MT5 ID.
2. Admin approves/rejects.
3. Similar webhook flow (/internal/bc-approved or /internal/bc-rejected) clears the Telegram buttons.

---

## 3. CRITICAL Quirks & Known Issues (DO NOT BREAK THESE)

### Frontend: Mobile WebView Caching (pi.ts)
*   **DO NOT REMOVE CACHE-BUSTING:** In rontend/src/lib/api.ts, there is aggressive cache-busting (config.params._t = Date.now() and Cache-Control: no-cache). 
*   **Why:** The frontend is used inside mobile WebViews (iOS/Android) which have notoriously uncontrollable caching layers. If the cache-busting headers are removed, the WebView will permanently cache empty arrays or 401s, causing the app to freeze showing "No Orders".
*   *Note:* The UI aggressively polls (efetchInterval: 30000).

### Backend: Missing Server-Side Authentication
*   **SECURITY DEBT:** While the Next.js frontend handles JWTs and the Telegram Bot passes an X-Admin-Key header (_admin_headers() in pi_client.py), the **FastAPI backend currently lacks a dependency to enforce these keys on admin routes** (e.g., orders.py, dmin.py, installments.py).
*   If instructed to secure the backend, you must implement a dependency in security.py that validates *both* the Authorization: Bearer (from Next.js) and the X-Admin-Key (from the Bot), otherwise you will break the pipeline.

### Telegram Bot: Ephemeral State & Double Notifications
*   **dmin_messages.json is ephemeral:** The bot stores message IDs in a local JSON file to know which buttons to clear when a webhook arrives. Because Render wipes local storage on every deployment/restart, the bot forgets old message IDs.
*   **Already Processed Handling:** If an admin clicks an old Telegram button that was already processed in the web dashboard, the backend returns HTTP 400. ot.py is specifically programmed to catch "already" or "not pending" in the error text and gracefully clear the buttons anyway. Do not remove this error handling (query.edit_message_text(f"?? Order was already processed.")).
*   **Double Messaging:** Be careful adding user notifications. Both the Backend (orders.py/licenses.py) and the Bot (ot.py) have logic to send Telegram messages. Ensure you don't send duplicate "Approved" or "Rejected" messages to the customer.

### Python Variable Scoping in Webhooks
*   **FastAPI Background Tasks:** When triggering a webhook from a backend endpoint (e.g., licenses.py), do not place import os below the nested webhook function definition. Python's lexical scoping will throw a NameError: cannot access free variable 'os'. Always place imports globally or at the top of the nested function.

---

## 4. Environment Variables Reference
*   DATABASE_URL (Supabase AsyncPG format)
*   TELEGRAM_BOT_TOKEN
*   ADMIN_CHAT_ID, VPS_ADMIN_CHAT_ID
*   TELEGRAM_WEBHOOK_URL (Points to the bot's internal domain for cross-communication)
*   NEXT_PUBLIC_API_URL
*   SECRET_KEY (For JWT)

*End of Memory Dump. Proceed with confidence.*
