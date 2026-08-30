import re

def fix_vps_ui():
    with open('src/app/admin/vps/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    status_dropdown_code = '''
const StatusDropdown = ({ order, onStatusChange }: { order: any, onStatusChange: (id: number, status: string) => void }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const statusColor = getStatusColor(order.status);
  const dropdownRef = React.useRef<HTMLDivElement>(null);
  
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => {
            if(order.status !== 'provisioned') setIsOpen(!isOpen);
        }}
        disabled={order.status === 'provisioned'}
        className={lex items-center justify-between w-32 border text-xs rounded-full px-3 py-1.5 font-medium focus:outline-none transition-colors  }
      >
        <span>● {order.status.charAt(0).toUpperCase() + order.status.slice(1)}</span>
        {order.status !== 'provisioned' && (
          <svg className={w-3 h-3 transition-transform } fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
        )}
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-32 bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl z-50 overflow-hidden">
          {['pending', 'contacted', 'paid', 'provisioned'].map(s => (
            <div 
              key={s} 
              onClick={() => { onStatusChange(order.id, s); setIsOpen(false); }} 
              className={px-4 py-2 text-xs cursor-pointer transition-colors hover:bg-neutral-800 flex items-center }
            >
              <span className={mr-2 }>●</span> 
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
'''

    # Ensure React is imported
    if "import React" not in content and "import * as React" not in content:
        content = content.replace("import { useState }", "import React, { useState }")
        
    # Insert StatusDropdown after getStatusColor
    content = content.replace("export default function VpsOrdersPage() {", status_dropdown_code + "\nexport default function VpsOrdersPage() {")

    # Replace the select tag
    old_select = re.search(r'<select[\s\S]*?</select>', content)
    if old_select:
        new_select = "<StatusDropdown order={order} onStatusChange={(id, st) => statusMutation.mutate({ id, status: st })} />"
        content = content.replace(old_select.group(0), new_select)
        with open('src/app/admin/vps/page.tsx', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully updated VPS UI")
    else:
        print("Could not find select tag")

fix_vps_ui()
