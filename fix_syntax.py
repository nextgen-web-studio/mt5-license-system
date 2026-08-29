with open('frontend/src/app/admin/licenses/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('await api.post(/api/v1/licenses//recompile);', 'await api.post(`/api/v1/licenses/${license.id}/recompile`);')

with open('frontend/src/app/admin/licenses/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("FIXED")
