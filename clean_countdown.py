with open("frontend/src/app/admin/layout.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "// Auto-refresh countdown display" in line:
        skip = True
        continue
    if skip and "return () => clearInterval(timer);" in line:
        pass
    if skip and "}, []);" in line:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open("frontend/src/app/admin/layout.tsx", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Cleaned up countdown logic")
