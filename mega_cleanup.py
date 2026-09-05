import os, shutil

# ─── BACKEND ───────────────────────────────────────────────────────────────────
backend_delete = [
    "backend/alter_db.py",
    "backend/alter_db_installments.py",
    "backend/alter_db_trials.py",
    "backend/check_db.py",
    "backend/clear_db.py",
    "backend/create_db.py",
    "backend/fix_db.py",
    "backend/fix_db_28.py",
    "backend/infinity_trader.db",
    "backend/infinity_trading.db",
    "backend/metaeditor64.zip",
    "backend/migrate_sqlite.py",
    "backend/mt5_license.db",
    "backend/patch_vps_durations.py",
    "backend/run_migration.py",
    "backend/seed_products.py",
    "backend/test.db",
    "backend/test_hash.py",
    "backend/test_hash2.py",
    "backend/test_query.py",
    "backend/wipe_db.py",
    "backend/wipe_prod.py",
]
backend_delete_dirs = [
    "backend/__pycache__",
    "backend/cd",
    "backend/npm",
    "backend/python",
]

# ─── FRONTEND ──────────────────────────────────────────────────────────────────
frontend_delete = [
    "frontend/AGENTS.md",
    "frontend/CLAUDE.md",
    "frontend/fix_dropdown_syntax.py",
    "frontend/fix_providers.py",
    "frontend/fix_queries.py",
    "frontend/fix_react.py",
    "frontend/fix_rupee.py",
    "frontend/fix_rupee2.py",
    "frontend/fix_rupee3.py",
    "frontend/fix_toast1.py",
    "frontend/fix_vps_dropdown.py",
    "frontend/fix_vps_optimistic.py",
    "frontend/fix_vps_syntax.py",
    "frontend/fix_vps_ui.py",
    "frontend/replace_alerts.py",
    "frontend/speed_polling.py",
]

# ─── WINDOWS-WORKER ────────────────────────────────────────────────────────────
worker_delete = [
    "windows-worker/.env.example",
    "windows-worker/check_buckets.py",
    "windows-worker/check_db.py",
    "windows-worker/connectivity_test.py",
    "windows-worker/inspect_job.py",
    "windows-worker/inspect_jobs.py",
    "windows-worker/reset_jobs.py",
    "windows-worker/test.bat",
    "windows-worker/test_claim.py",
    "windows-worker/test_delivery.py",
    "windows-worker/test_delivery_30.py",
    "windows-worker/test_download.py",
    "windows-worker/test_httpx_multipart.py",
    "windows-worker/test_signed_url.py",
    "windows-worker/test_telegram_api.py",
    "windows-worker/worker_service.log",
]
worker_delete_dirs = [
    "windows-worker/__pycache__",
]

# ─── TELEGRAM BOT ──────────────────────────────────────────────────────────────
bot_delete_dirs = [
    "telegram_bot/__pycache__",
]

# ─── ROOT ──────────────────────────────────────────────────────────────────────
root_delete = [
    "ANTIGRAVITY_MEMORY.md",
]

# Execute deletions
deleted = []
errors = []

all_files = backend_delete + frontend_delete + worker_delete + root_delete
for f in all_files:
    if os.path.isfile(f):
        os.remove(f)
        deleted.append(f)
    else:
        errors.append(f"NOT FOUND: {f}")

all_dirs = backend_delete_dirs + worker_delete_dirs + bot_delete_dirs
for d in all_dirs:
    if os.path.isdir(d):
        shutil.rmtree(d)
        deleted.append(d)
    else:
        errors.append(f"DIR NOT FOUND: {d}")

print(f"Deleted {len(deleted)} items:")
for d in deleted:
    print(f"  OK: {d}")

if errors:
    print(f"\nWarnings ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
