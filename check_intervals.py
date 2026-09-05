import os

for root, dirs, files in os.walk("frontend/src/app/admin"):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "refetchInterval" in content:
                import re
                intervals = re.findall(r"refetchInterval:\s*\d+", content)
                print(f"{path}: {intervals}")
