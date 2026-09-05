import re
with open("frontend/src/app/admin/layout.tsx", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'  // Auto-refresh countdown display\n  useEffect\(\(\) => \{\n    const timer = setInterval\(\(\) => \{\n      setCountdown\(prev => \{\n        if \(prev <= 1\) return 5;\n        return prev - 1;\n      \}\);\n    \}, 1000\);\n    return \(\) => clearInterval\(timer\);\n  \}, \[\]\);\n'
content = re.sub(pattern, "", content)

with open("frontend/src/app/admin/layout.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Removed useEffect countdown")
