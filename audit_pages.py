import os, re

admin_pages = []
for root, dirs, files in os.walk("frontend/src/app/admin"):
    for file in files:
        if file == "page.tsx":
            admin_pages.append(os.path.join(root, file))

issues = {}
for page in admin_pages:
    with open(page, "r", encoding="utf-8") as f:
        content = f.read()
    page_issues = []
    
    # Check 1: uses isLoading for spinner (causes lag on cached refetch)
    if "isLoading)" in content or "isLoading )" in content:
        page_issues.append("Uses isLoading for spinner (causes flash when data is stale)")
    
    # Check 2: missing placeholderData/keepPreviousData
    if "useQuery" in content and "placeholderData" not in content:
        page_issues.append("Missing placeholderData: keepPreviousData")
    
    # Check 3: has own staleTime that overrides global
    if "staleTime" in content:
        vals = re.findall(r"staleTime:\s*(\d+)", content)
        page_issues.append(f"Has own staleTime override: {vals}")
    
    if page_issues:
        issues[page] = page_issues

for page, i in issues.items():
    print(f"\n{page}:")
    for issue in i:
        print(f"  - {issue}")
