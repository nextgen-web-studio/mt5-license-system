import os
import re

admin_dir = r"C:\temp-repo\frontend\src\app\admin"

for root, _, files in os.walk(admin_dir):
    for file in files:
        if file == "page.tsx":
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if "window.location.reload()" not in content:
                continue

            print(f"Fixing {path}")
            
            # 1. Add useQueryClient import
            if "useQueryClient" not in content:
                content = content.replace("useQuery } from '@tanstack/react-query'", "useQuery, useQueryClient } from '@tanstack/react-query'")
            
            # 2. Add queryClient inside component
            comp_match = re.search(r"export default function \w+\(\) {", content)
            if comp_match and "const queryClient = useQueryClient();" not in content:
                content = content.replace(comp_match.group(0), f"{comp_match.group(0)}\n  const queryClient = useQueryClient();")

            # 3. Replace delete logic
            qkey_match = re.search(r"queryKey:\s*\['(.*?)'\]", content)
            if qkey_match:
                query_key = qkey_match.group(1)
                
                def replacer(m):
                    api_call = m.group(1)
                    return f"""// Optimistic UI update for instant response
            queryClient.setQueryData(['{query_key}'], (old: any) => old?.filter((item: any) => item.id !== deletingId));
            {api_call}
            queryClient.invalidateQueries({{ queryKey: ['{query_key}'] }});"""

                content = re.sub(r"(await api\.delete\(.*?\);)\s*window\.location\.reload\(\);", replacer, content)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

print("Done fixing delays!")
