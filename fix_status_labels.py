with open("frontend/src/app/admin/vps/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Add pending_admin_approval to STATUS_LABELS
content = content.replace(
    "const STATUS_LABELS: Record<string, string> = {\n  pending: 'Pending',\n  contacted: 'Contacted',",
    "const STATUS_LABELS: Record<string, string> = {\n  pending: 'Pending',\n  pending_admin_approval: 'Pending',\n  contacted: 'Contacted',"
)

# Use STATUS_LABELS everywhere for the renewal badges too!
content = content.replace(
    "{order.status === 'pending_admin_approval' ? 'Pending' : (order.status || 'Unknown').replace(/_/g, ' ')}",
    "{STATUS_LABELS[order.status] || (order.status || 'Unknown').replace(/_/g, ' ')}"
)

with open("frontend/src/app/admin/vps/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated STATUS_LABELS")
