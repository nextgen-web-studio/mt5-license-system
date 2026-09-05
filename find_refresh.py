import os
for root, dirs, files in os.walk("frontend/src"):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read()
                if "refetchInterval" in content:
                    print(f"refetchInterval in {os.path.join(root, file)}")
                if "Live Updates" in content or "Live Refresh" in content or "Auto Refresh" in content:
                    print(f"Live Refresh in {os.path.join(root, file)}")
