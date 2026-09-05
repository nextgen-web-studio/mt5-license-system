import re

with open("frontend/src/app/admin/installments/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace any garbled string like ',1' or '?' before '${payAmount}' with '₹'
content = re.sub(r"payment of [^$]*\$\{payAmount\}", "payment of ₹${payAmount}", content)

with open("frontend/src/app/admin/installments/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed rupees properly")
