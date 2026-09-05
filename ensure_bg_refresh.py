import os

for root, dirs, files in os.walk("frontend/src/app/admin"):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "refetchIntervalInBackground" in content and "refetchIntervalInBackground: true" not in content:
                print(f"MISSING refetchIntervalInBackground: true in {path}")
            elif "refetchIntervalInBackground: true" in content:
                print(f"OK: {path}")
            else:
                # Add refetchIntervalInBackground: true after refetchInterval: 5000
                if "refetchInterval: 5000," in content:
                    content = content.replace("refetchInterval: 5000,", "refetchInterval: 5000,\n      refetchIntervalInBackground: true,")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Added refetchIntervalInBackground to {path}")
