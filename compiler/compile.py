import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
import re

# ---------------------------------------------------------------------------
# Paths - always absolute, built with pathlib
# ---------------------------------------------------------------------------
METAEDITOR = Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe")

BASE_DIR    = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR   = BASE_DIR / "output"

def _log(level: str, message: str) -> None:
    print(f"[{level}] {message}")

def normalize_expiry(expiry: str) -> str:
    expiry = expiry.strip()
    if expiry.lower() in ("lifetime", "none", ""):
        return "lifetime"
    for fmt in ("%Y-%m-%d",):
        try:
            dt = datetime.strptime(expiry, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    parts = expiry.split("-")
    if len(parts) == 4:
        year_str, p1, p2, day_str = parts
        month_str = p1 + p2
        try:
            dt = datetime(int(year_str), int(month_str), int(day_str))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    raise ValueError("Cannot normalize expiry date")

def compile_ea(mt5_id: str, expiry: str, plan: str, source_code: str = None) -> str:
    _log("INFO", "Starting compilation")
    _log("INFO", f"MT5 ID              : {mt5_id}")
    _log("INFO", f"Plan                : {plan}")
    
    normalized_expiry = normalize_expiry(expiry)
    _log("INFO", f"Expiry (normalized) : {normalized_expiry}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    template_path = TEMPLATE_DIR / "bot.mq5"

    if not METAEDITOR.exists():
        raise FileNotFoundError(f"MetaEditor not found: {METAEDITOR}")

    if not source_code:
        if not template_path.exists():
            raise FileNotFoundError(f"EA template not found: {template_path}")
        source_code = template_path.read_text(encoding="utf-8")

    file_label = normalized_expiry
    output_name = f"InfinityTrader_{mt5_id}_{file_label}.ex5"
    source_name = f"InfinityTrader_{mt5_id}_{file_label}.mq5"
    source_path = OUTPUT_DIR / source_name
    ex5_path    = OUTPUT_DIR / output_name

    # Check for legacy Handlebars format or new Regex format
    if "{{MT5_ID}}" in source_code:
        _log("INFO", "Using legacy Handlebars replacement")
        source_code = source_code.replace("{{MT5_ID}}", str(mt5_id))
        source_code = source_code.replace("{{EXPIRY}}", normalized_expiry)
        source_code = source_code.replace("{{PLAN}}",   str(plan))
    else:
        _log("INFO", "Using Python Regex injection")
        # Format the expiry for MQL5 Date format (D'YYYY.MM.DD')
        mql5_expiry = normalized_expiry.replace("-", ".") if normalized_expiry != "lifetime" else "2099.01.01"
        source_code = re.sub(r'int\s+ALLOWED_MT5_ID\s*=\s*\d+;', f'int ALLOWED_MT5_ID = {mt5_id};', source_code)
        source_code = re.sub(r'datetime\s+LICENSE_EXPIRY\s*=\s*D\'[^\']*\';', f'datetime LICENSE_EXPIRY = D\'{mql5_expiry}\';', source_code)

    source_path.write_text(source_code, encoding="utf-8")

    if ex5_path.exists():
        ex5_path.unlink()

    command = [str(METAEDITOR), f"/compile:{source_path}", "/log"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)

    if not ex5_path.exists():
        raise RuntimeError("MetaEditor failed.\\nSTDOUT: " + str(result.stdout) + "\\nSTDERR: " + str(result.stderr))

    _log("INFO",  "Compilation successful")
    return str(ex5_path)
