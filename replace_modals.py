import os
import re

def add_modal(filepath, title, msg, api_endpoint, id_attr):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add imports
    if 'import ConfirmModal' not in content:
        content = content.replace("import api from '@/lib/api';", "import api from '@/lib/api';\nimport ConfirmModal from '@/components/ui/ConfirmModal';\nimport { useState } from 'react';")
    
    # State hooks
    hooks = '''  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | string | null>(null);
'''
    if 'setDeleteModalOpen' not in content:
        content = re.sub(r'(export default function [^)]+\) \{)', r'\1\n' + hooks, content)

    # UI modal
    modal_ui = f'''
      <ConfirmModal
        isOpen={{deleteModalOpen}}
        title="{title}"
        message="{msg}"
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={{async () => {{
          if(!deletingId) return;
          try {{
            await api.delete(`{api_endpoint}/${{deletingId}}`);
            window.location.reload();
          }} catch(e) {{
            // Ignore error
          }}
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}}}
        onCancel={{() => {{
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}}}
      />
    '''
    
    # Replace onClick handlers
    if filepath.endswith('ea-template/page.tsx'):
        # onClick={() => handleDelete(v.id)}
        content = re.sub(
            r'onClick=\{\(\) => handleDelete\([^)]+\)\}',
            r'onClick={() => { setDeletingId(' + id_attr + '); setDeleteModalOpen(true); }}',
            content
        )
    elif filepath.endswith('licenses/page.tsx'):
        # onClick={() => { if (confirm('Are you sure you want to delete this license?')) { deleteLicenseMutation.mutate(license.id); } }}
        content = re.sub(
            r'onClick=\{\(\) => \{\s*if \(confirm\([^)]+\)\) \{\s*deleteLicenseMutation\.mutate\([^)]+\);\s*\}\s*\}\}',
            r'onClick={() => { setDeletingId(' + id_attr + '); setDeleteModalOpen(true); }}',
            content
        )
    elif filepath.endswith('products/page.tsx'):
        content = re.sub(
            r'onClick=\{\(\) => \{\s*if \(confirm\([^)]+\)\) \{\s*deleteProductMutation\.mutate\([^)]+\);\s*\}\s*\}\}',
            r'onClick={() => { setDeletingId(' + id_attr + '); setDeleteModalOpen(true); }}',
            content
        )
    elif filepath.endswith('trial/page.tsx'):
        # onClick={async () => { if (!grantTg) return; if (!confirm(...)) return; ... }}
        content = re.sub(
            r'onClick=\{async \(\) => \{\s*if \(!grantTg\) return;\s*if \(!confirm\([^)]+\)\) return;\s*try \{\s*await api\.delete\(`/api/v1/trials/admin/reset/\$\{grantTg\}`\);\s*alert\(\'Trial history successfully cleared!\'\);\s*setGrantTg\(\'\'\);\s*\} catch \(e\) \{\s*alert\(\'Failed to reset trial history\. \' \+ e\);\s*\}\s*\}\}',
            r'onClick={() => { if(!grantTg) return; setDeletingId(grantTg); setDeleteModalOpen(true); }}',
            content
        )

    # Insert modal at end of container
    if 'ConfirmModal' not in content[content.rfind('</div>'):]:
        content = content[:content.rfind('</div>')] + modal_ui + '\n</div>'

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

add_modal('frontend/src/app/admin/ea-template/page.tsx', 'Delete EA Template', 'Are you sure you want to delete this EA template? This cannot be undone.', '/api/v1/ea-templates/admin', 'v.id')
add_modal('frontend/src/app/admin/licenses/page.tsx', 'Delete License', 'Are you sure you want to permanently delete this license? This will revoke access.', '/api/v1/licenses', 'license.id')
add_modal('frontend/src/app/admin/products/page.tsx', 'Delete Product', 'Are you sure you want to delete this product? All active subscriptions will remain but it will hide the product from new customers.', '/api/v1/products', 'product.id')
add_modal('frontend/src/app/admin/trial/page.tsx', 'Reset Trial History', 'Are you sure you want to permanently delete this user trial history? They will be able to claim a free trial immediately.', '/api/v1/trials/admin/reset', 'grantTg')
