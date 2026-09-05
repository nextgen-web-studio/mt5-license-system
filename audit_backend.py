import os, re

# Find and fix duplicate import patterns in bot and backend
# Check backend for import inside functions (bad practice)
for root, dirs, files in os.walk("backend/app/api/v1/endpoints"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # Find inline imports
            inline = re.findall(r"    import (?:os|httpx|asyncio),? (?:httpx|asyncio|os),? ?(?:asyncio|os)?", content)
            if inline:
                print(f"{path}: {len(inline)} inline imports found - {set(inline)}")

# Check for duplicate route paths
print("\n--- Checking for duplicate routes ---")
for root, dirs, files in os.walk("backend/app/api/v1/endpoints"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            routes = re.findall(r'@router\.(get|post|put|delete)\("([^"]+)"', content)
            seen = {}
            for method, route in routes:
                key = f"{method.upper()} {route}"
                if key in seen:
                    print(f"DUPLICATE ROUTE in {path}: {key}")
                seen[key] = True
print("Done")
