import re, os

# Fix all inline imports - move them to top of each file
files_to_fix = [
    "backend/app/api/v1/endpoints/admin.py",
    "backend/app/api/v1/endpoints/installments.py",
    "backend/app/api/v1/endpoints/licenses.py",
    "backend/app/api/v1/endpoints/orders.py",
    "backend/app/api/v1/endpoints/trials.py",
]

for path in files_to_fix:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check what top-level imports already exist
    has_os = bool(re.search(r"^import os\b", content, re.MULTILINE))
    has_httpx = bool(re.search(r"^import httpx\b", content, re.MULTILINE))
    has_asyncio = bool(re.search(r"^import asyncio\b", content, re.MULTILINE))
    
    # Remove all inline import os, httpx, asyncio patterns (various combos)
    content = re.sub(r"\n    import os, httpx, asyncio\n", "\n", content)
    content = re.sub(r"\n    import os, asyncio\n", "\n", content)
    content = re.sub(r"\n    import asyncio, httpx\n", "\n", content)
    content = re.sub(r"\n    import os, asyncio, \n", "\n", content)
    
    # Add missing top-level imports at the very top (after existing imports block)
    # Find the last import line near the top
    import_section_end = 0
    for m in re.finditer(r"^(?:import|from) .+$", content, re.MULTILINE):
        import_section_end = m.end()
    
    additions = []
    if not has_os:
        additions.append("import os")
    if not has_httpx:
        additions.append("import httpx")
    if not has_asyncio:
        additions.append("import asyncio")
    
    if additions:
        insert_pos = import_section_end
        content = content[:insert_pos] + "\n" + "\n".join(additions) + content[insert_pos:]
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Fixed inline imports in {path}")
