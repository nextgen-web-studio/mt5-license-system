import re
with open("frontend/src/app/admin/layout.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the live refresh indicator UI
pattern = r'<div className="hidden md:flex items-center gap-2 px-3 py-1\.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">.*?</div>'
content = re.sub(pattern, "", content, flags=re.DOTALL)

with open("frontend/src/app/admin/layout.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Removed live refresh UI")
