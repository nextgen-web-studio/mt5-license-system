import re

def fix_vps():
    with open('src/app/admin/vps/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the broken select tag
    old_select = re.search(r'<select\s+value=\{order\.status\}\s+onChange=\{[\s\S]*?</select>', content)
    
    if old_select:
        new_select = """<select
                        value={order.status}
                        onChange={(e) => statusMutation.mutate({ id: order.id, status: e.target.value })}
                        disabled={order.status === 'provisioned'}
                        className={`border text-xs rounded-full px-3 py-1.5 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/50 appearance-none cursor-pointer transition-colors ${getStatusColor(order.status)} ${order.status === 'provisioned' ? 'opacity-70 cursor-not-allowed' : 'hover:opacity-80'}`}
                      >
                        <option value="pending" className="bg-neutral-900 text-yellow-500">● Pending</option>
                        <option value="contacted" className="bg-neutral-900 text-blue-400">● Contacted</option>
                        <option value="paid" className="bg-neutral-900 text-purple-400">● Paid</option>
                        <option value="provisioned" className="bg-neutral-900 text-emerald-400">● Provisioned</option>
                      </select>"""
        content = content.replace(old_select.group(0), new_select)
        
        with open('src/app/admin/vps/page.tsx', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed syntax error")
    else:
        print("Could not find the broken select tag")

fix_vps()
