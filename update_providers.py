with open("frontend/src/app/providers.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("staleTime: 60 * 1000,", "staleTime: 5 * 60 * 1000, // 5 minutes lightning fast cache")

with open("frontend/src/app/providers.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated staleTime")
