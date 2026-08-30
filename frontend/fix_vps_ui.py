import re

def rewrite_vps_ui():
    with open('src/app/admin/vps/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add the helper function right before the main component
    helper = '''const getStatusColor = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'pending': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'contacted': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    case 'paid': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    case 'provisioned': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    default: return 'bg-neutral-800 text-neutral-400 border-neutral-700';
  }
};

export default function VpsOrdersPage() {'''
    content = content.replace('export default function VpsOrdersPage() {', helper, 1)

    # Replace the select element
    old_select = '''<select
                        value={order.status}
                        onChange={(e) => statusMutation.mutate({ id: order.id, status: e.target.value })}
                        disabled={order.status === 'provisioned'}
                        className="bg-neutral-950 border border-neutral-800 text-xs rounded px-2 py-1 focus:outline-none focus:border-blue-500"
                      >
                        <option value="pending">Pending</option>
                        <option value="contacted">Contacted</option>
                        <option value="paid">Paid</option>
                        <option value="provisioned">Provisioned</option>
                      </select>'''

    new_select = '''<select
                        value={order.status}
                        onChange={(e) => statusMutation.mutate({ id: order.id, status: e.target.value })}
                        disabled={order.status === 'provisioned'}
                        className={order text-xs rounded-full px-3 py-1.5 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/50 appearance-none cursor-pointer transition-colors  }
                      >
                        <option value="pending" className="bg-neutral-900 text-yellow-500">● Pending</option>
                        <option value="contacted" className="bg-neutral-900 text-blue-400">● Contacted</option>
                        <option value="paid" className="bg-neutral-900 text-purple-400">● Paid</option>
                        <option value="provisioned" className="bg-neutral-900 text-emerald-400">● Provisioned</option>
                      </select>'''

    content = content.replace(old_select, new_select)

    with open('src/app/admin/vps/page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)

rewrite_vps_ui()
print("Updated VPS UI")
