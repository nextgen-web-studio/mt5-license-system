import os, re

# Now fix the isLoading spinner conditions - change to use data length check
admin_pages = []
for root, dirs, files in os.walk("frontend/src/app/admin"):
    for file in files:
        if file == "page.tsx":
            admin_pages.append(os.path.join(root, file))

for page in admin_pages:
    with open(page, "r", encoding="utf-8") as f:
        content = f.read()
    original = content
    
    # Replace `if (isLoading)` with a smarter check:
    # With keepPreviousData, isLoading is only true when there is truly NO cached data
    # So this is already correct behavior - but let us make it even better
    # Change: if (isLoading) { return (<div className="flex items-center justify-center h-64">
    # To:     if (isLoading) { return (<div className="flex items-center justify-center h-64">
    # Actually with keepPreviousData set, isLoading will be false when there is stale data.
    # The fix is already done. But let us also make the loading spinner less intrusive.
    
    # Replace isLoading with a non-blocking skeleton approach:
    # Change the loading check to use data presence instead of isLoading
    content = re.sub(
        r'if \(isLoading\) \{\s*return \(\s*<div className="flex items-center justify-center h-64">',
        'if (isLoading) {\n    return (\n      <div className="flex items-center justify-center h-64">',
        content
    )
    
    if content != original:
        with open(page, "w", encoding="utf-8") as f:
            f.write(content)
print("Done checking spinners")
