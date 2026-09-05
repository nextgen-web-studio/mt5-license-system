import os, re

admin_pages = []
for root, dirs, files in os.walk("frontend/src/app/admin"):
    for file in files:
        if file == "page.tsx":
            admin_pages.append(os.path.join(root, file))

fixed = []
for page in admin_pages:
    with open(page, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # 1. Replace isLoading with !data (only show spinner when truly no data at all)
    # Pattern: if (isLoading) { return (<div className="flex items-center justify-center h-64">
    # Replace isLoading check with: the query's isPending (which is only true on first-ever load, not cached refetch)
    content = re.sub(
        r'const \{ data: ([^,]+)(?:[^}]*), isLoading(?:[^}]*)\} = useQuery\(',
        lambda m: m.group(0).replace(', isLoading', ', isLoading, isFetching'),
        content
    )
    
    # 2. Replace every "if (isLoading)" with "if (isLoading && !isFetching)" — no wait
    # The correct fix: isLoading is true only when BOTH: no data AND isFetching
    # So "isLoading" alone = "no cached data AND currently fetching" = true first load only
    # But React Query v5: isLoading = isPending && isFetching
    # The problem is they show a spinner on EVERY refetch
    # Fix: change the spinner condition from isLoading to (isLoading && !data?.length)
    
    # Actually the cleanest fix: add placeholderData: keepPreviousData to every useQuery
    # This makes isLoading = false when there's previous data
    
    # Add keepPreviousData import
    if "keepPreviousData" not in content and "from '@tanstack/react-query'" in content:
        content = content.replace(
            "from '@tanstack/react-query'",
            "from '@tanstack/react-query'"  # Will handle import separately
        )
        # Add keepPreviousData to the import
        content = re.sub(
            r"import \{([^}]+)\} from '@tanstack/react-query'",
            lambda m: f"import {{{m.group(1).rstrip()}, keepPreviousData}} from '@tanstack/react-query'" 
                      if 'keepPreviousData' not in m.group(1) else m.group(0),
            content
        )
    
    # Add placeholderData: keepPreviousData to every useQuery block that has refetchInterval
    content = re.sub(
        r"(refetchInterval: 5000,\n\s*refetchIntervalInBackground: true,)",
        r"\1\n      placeholderData: keepPreviousData,",
        content
    )
    
    if content != original:
        with open(page, "w", encoding="utf-8") as f:
            f.write(content)
        fixed.append(page)
        print(f"Fixed: {page}")
    else:
        print(f"No change: {page}")

print(f"\nTotal fixed: {len(fixed)}")
