# Update the logout button to match nav items exactly, and move it into nav as a red styled item
with open("frontend/src/app/admin/layout.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the entire bottom section with logout
old = """        <div className="p-4 md:p-4 border-t border-neutral-800 shrink-0 space-y-2 pb-8 md:pb-4">
          
          <button 
            onClick={() => {
              document.cookie = 'admin_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
              window.location.href = '/login';
            }}
            className="flex items-center space-x-3 px-3 py-2.5 w-full rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800/50 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>"""

new = """        <div className="p-3 border-t border-neutral-800 shrink-0 pb-8 md:pb-4">
          <button 
            onClick={() => {
              document.cookie = 'admin_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
              window.location.href = '/login';
            }}
            className="flex items-center space-x-3 px-3 py-2 md:py-2.5 w-full rounded-lg text-sm md:text-base text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>"""

content = content.replace(old, new)

with open("frontend/src/app/admin/layout.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated logout button")
