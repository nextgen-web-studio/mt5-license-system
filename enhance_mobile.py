import os
import re

admin_dir = r"C:\temp-repo\frontend\src\app\admin"

for root, _, files in os.walk(admin_dir):
    for file in files:
        if file == "page.tsx":
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            modified = False

            # 1. Hide ugly scrollbar track
            old_overflow = 'className="overflow-x-auto"'
            new_overflow = 'className="overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"'
            if old_overflow in content:
                content = content.replace(old_overflow, new_overflow)
                modified = True
                
            # 2. Make top action buttons full width on mobile
            # Looking for buttons that have bg-emerald-600, bg-indigo-600, or bg-blue-600 in the header
            # They usually start with className="flex items-center px-4 py-2 bg-...
            def btn_replacer(m):
                cls_str = m.group(1)
                if 'w-full md:w-auto justify-center' not in cls_str:
                    new_cls = 'w-full md:w-auto justify-center ' + cls_str
                    return f'className="{new_cls}"'
                return m.group(0)

            # Match generic primary buttons
            new_content = re.sub(r'className="(flex items-center px-4 py-2 bg-(?:emerald|indigo|blue)-600.*?)"', btn_replacer, content)
            if new_content != content:
                content = new_content
                modified = True
                
            if modified:
                print(f"Enhancing mobile UI in {path}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

print("Done enhancing mobile UI!")
