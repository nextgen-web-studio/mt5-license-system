import re
import glob

def fix_all_queries():
    files = glob.glob('src/app/admin/**/page.tsx', recursive=True) + ['src/app/admin/page.tsx']
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        modified = False
        
        # 1. Add refetchIntervalInBackground: true
        if 'refetchInterval: 10000' in content and 'refetchIntervalInBackground' not in content:
            content = content.replace('refetchInterval: 10000,', 'refetchInterval: 10000,\n    refetchIntervalInBackground: true,')
            modified = True
            
        # Also add it to compiler jobs if not there
        if 'compiler' in file and 'refetchInterval' not in content and 'admin-compiler-jobs' in content:
            content = content.replace("queryKey: ['admin-compiler-jobs'],", "queryKey: ['admin-compiler-jobs'],\n    refetchInterval: 10000,\n    refetchIntervalInBackground: true,")
            modified = True
            
        # Admin stats also might need it
        if file.endswith('admin\\\\page.tsx') or file.endswith('admin/page.tsx'):
            if 'admin-stats' in content and 'refetchInterval' not in content:
                content = content.replace("queryKey: ['admin-stats'],", "queryKey: ['admin-stats'],\n    refetchInterval: 10000,\n    refetchIntervalInBackground: true,")
                modified = True
                
        # Products
        if 'admin-products' in content and 'refetchInterval' not in content:
            content = content.replace("queryKey: ['admin-products'],", "queryKey: ['admin-products'],\n    refetchInterval: 10000,\n    refetchIntervalInBackground: true,")
            modified = True

        # 2. Fix if (error) {
        # We need to know the data variable.
        # Format: const { data: whatever = [], isLoading, error } = useQuery
        # or const { data: stats, isLoading, error } = useQuery
        match = re.search(r'const\s*\{\s*data\s*:\s*([a-zA-Z0-9_]+)(?:\s*=\s*\[\])?\s*,.*?error.*?\}\s*=\s*useQuery', content)
        if match:
            var_name = match.group(1)
            # Find if (error) {
            if 'if (error) {' in content:
                # Replace with checking if var_name is empty or null
                # Because if it's stats, it's an object, so checking length might fail.
                # Let's check if (error && (!%s || (Array.isArray(%s) && %s.length === 0))) {
                new_condition = f"if (error && (!{var_name} || (Array.isArray({var_name}) && {var_name}.length === 0) || (typeof {var_name} === 'object' && Object.keys({var_name}).length === 0))) {{"
                content = content.replace('if (error) {', new_condition)
                modified = True
                
        if modified:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {file}")

fix_all_queries()
