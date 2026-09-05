import re
with open("frontend/src/app/admin/vps/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Find all occurrences of the class string
pattern = r"(order\.status === 'delivered' \|\| order\.status === 'provisioned' \? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :)\s*('bg-yellow-500/10 text-yellow-400 border-yellow-500/20')"

content = re.sub(pattern, r"\1\n                            order.status === 'rejected' ? 'bg-red-500/10 text-red-400 border-red-500/20' :\n                            \2", content)

with open("frontend/src/app/admin/vps/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated desktop styling regex")
