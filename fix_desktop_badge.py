with open("frontend/src/app/admin/vps/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

target = """                              order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                            }`"""

replacement = """                              order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              order.status === 'rejected' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                              'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                            }`"""

content = content.replace(target, replacement)

# Replace the desktop text renderer too!
content = content.replace(
    "{(order.status || 'Unknown').replace(/_/g, ' ')}",
    "{STATUS_LABELS[order.status] || (order.status || 'Unknown').replace(/_/g, ' ')}"
)

with open("frontend/src/app/admin/vps/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated desktop styling")
