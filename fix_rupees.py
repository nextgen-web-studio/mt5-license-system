with open("frontend/src/app/admin/installments/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("payment of ?${payAmount}", "payment of ₹${payAmount}")
content = content.replace("remaining balance of ?${", "remaining balance of ₹${")

with open("frontend/src/app/admin/installments/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed rupees symbol")
