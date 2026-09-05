with open("frontend/src/app/admin/vps/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# First, fix the status color for 'rejected' on desktop
# Find the exact desktop rendering block
import re

content = re.sub(
    r"order\.status === 'delivered' \|\| order\.status === 'provisioned' \? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :\s*'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'",
    "order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :\n                            order.status === 'rejected' ? 'bg-red-500/10 text-red-400 border-red-500/20' :\n                            'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'",
    content
)

# Second, replace 'Pending Admin Approval' with 'Pending' for UI display
# The display logic uses: {(order.status || 'Unknown').replace(/_/g, ' ')}
# We want to change 'pending_admin_approval' to 'Pending' in the UI.

content = content.replace(
    "{(order.status || 'Unknown').replace(/_/g, ' ')}",
    "{order.status === 'pending_admin_approval' ? 'Pending' : (order.status || 'Unknown').replace(/_/g, ' ')}"
)

# And in mobile layout, it uses:
# {STATUS_LABELS[order.status] || (order.status || 'Unknown').replace(/_/g, ' ')}
# Let's check STATUS_LABELS
