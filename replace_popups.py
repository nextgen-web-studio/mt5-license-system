import os
import re

def update_orders():
    path = 'frontend/src/app/admin/orders/page.tsx'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Import ConfirmModal
    if 'import ConfirmModal' not in content:
        content = content.replace("import api from '@/lib/api';", "import api from '@/lib/api';\nimport ConfirmModal from '@/components/ui/ConfirmModal';\nimport { useState } from 'react';")
    
    # Check if useState is imported
    if 'useState' not in content:
        content = content.replace('import { useQuery }', "import { useState } from 'react';\nimport { useQuery }")
        
    hooks = '''  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | string | null>(null);
'''
    if 'setDeleteModalOpen' not in content:
        content = re.sub(r'(export default function [^)]+\) \{)', r'\1\n' + hooks, content)

    modal_ui = '''
      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Order"
        message="Are you sure you want to permanently delete this order? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={async () => {
          if(!deletingId) return;
          try {
            await api.delete(`/api/v1/orders/${deletingId}`);
            window.location.reload();
          } catch(e) {
            alert('Failed to delete');
          }
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}
        onCancel={() => {
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}
      />
    '''
    
    content = re.sub(
        r'onClick=\{async \(\) => \{\s*if\(confirm\([^\)]+\)\) \{\s*try \{\s*await api\.delete\([^\)]+\);\s*window\.location\.reload\(\);\s*\} catch\(e\) \{ alert\([^\)]+\); \}\s*\}\s*\}\}',
        r'onClick={() => { setDeletingId(order.id); setDeleteModalOpen(true); }}',
        content
    )
    
    if 'ConfirmModal' not in content[content.rfind('</div>'):]:
        content = content[:content.rfind('</div>')] + modal_ui + '\n</div>'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

update_orders()
