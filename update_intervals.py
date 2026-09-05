import os

for root, dirs, files in os.walk("frontend/src"):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "refetchInterval: 15000" in content or "refetchInterval: 10000" in content:
                content = content.replace("refetchInterval: 15000", "refetchInterval: 5000")
                content = content.replace("refetchInterval: 10000", "refetchInterval: 5000")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Updated {path}")
