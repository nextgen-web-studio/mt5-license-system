import re
with open("frontend/src/app/admin/layout.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the countdown state and effect
content = re.sub(r'const \[countdown, setCountdown\] = useState\(5\);\n', '', content)
content = re.sub(r'  useEffect\(\(\) => \{\n    const timer = setInterval\(\(\) => \{\n      setCountdown\(c => \(c === 1 \? 5 : c - 1\)\);\n    \}, 1000\);\n    return \(\) => clearInterval\(timer\);\n  \}, \[\]\);\n', '', content)

# Remove the UI div
pattern = r'<div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20">.*?<span className="text-xs text-emerald-400 font-medium">.*?</div>'
content = re.sub(pattern, "", content, flags=re.DOTALL)

with open("frontend/src/app/admin/layout.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Removed UI")
