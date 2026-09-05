import os
for root, dirs, files in os.walk("frontend/src"):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                if "QueryClient" in f.read():
                    print(f"Found in {os.path.join(root, file)}")
