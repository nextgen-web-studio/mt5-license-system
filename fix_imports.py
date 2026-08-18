import os

files = [
    'frontend/src/app/admin/ea-template/page.tsx',
    'frontend/src/app/admin/licenses/page.tsx',
    'frontend/src/app/admin/products/page.tsx',
    'frontend/src/app/admin/trial/page.tsx'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We only want to remove the duplicate 'import { useState } from 'react';'
    # that is right after the ConfirmModal import.
    content = content.replace("import ConfirmModal from '@/components/ui/ConfirmModal';\nimport { useState } from 'react';", "import ConfirmModal from '@/components/ui/ConfirmModal';")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
