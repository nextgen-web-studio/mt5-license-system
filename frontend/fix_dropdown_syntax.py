import re

def fix_vps_syntax2():
    with open('src/app/admin/vps/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    # We will just find the <button> block and replace it
    old_btn = re.search(r'<button[\s\S]*?className=\{[\s\S]*?\}[\s\S]*?>', content)
    if old_btn:
        new_btn = """<button 
        onClick={() => {
            if(order.status !== 'provisioned') setIsOpen(!isOpen);
        }}
        disabled={order.status === 'provisioned'}
        className={`flex items-center justify-between w-32 border text-xs rounded-full px-3 py-1.5 font-medium focus:outline-none transition-colors ${statusColor} ${order.status === 'provisioned' ? 'opacity-70 cursor-not-allowed' : 'hover:opacity-80 cursor-pointer'}`}
      >"""
        content = content.replace(old_btn.group(0), new_btn)
        with open('src/app/admin/vps/page.tsx', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed button syntax completely!")
    else:
        print("Could not find button block")

fix_vps_syntax2()
