import os

files = [
    'frontend/src/app/admin/ea-template/page.tsx',
    'frontend/src/app/admin/licenses/page.tsx',
    'frontend/src/app/admin/orders/page.tsx',
    'frontend/src/app/admin/products/page.tsx',
    'frontend/src/app/admin/trial/page.tsx'
]

for filepath in files:
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('\n  );\n}\n')
