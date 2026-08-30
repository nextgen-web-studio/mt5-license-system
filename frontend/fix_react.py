import re

def fix_react_imports():
    with open('src/app/admin/vps/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add useRef and useEffect to the react import
    old_import = "import { useState, FormEvent } from 'react';"
    new_import = "import { useState, FormEvent, useRef, useEffect } from 'react';"
    if old_import in content:
        content = content.replace(old_import, new_import)
    elif "useRef" not in content and "import React" not in content:
        # Fallback if it was changed
        content = "import React, { useRef, useEffect } from 'react';\n" + content

    # Replace React.*
    content = content.replace("React.useState", "useState")
    content = content.replace("React.useRef", "useRef")
    content = content.replace("React.useEffect", "useEffect")

    with open('src/app/admin/vps/page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)

fix_react_imports()
