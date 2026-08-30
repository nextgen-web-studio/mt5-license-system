import glob

def make_bulletproof():
    files = glob.glob('src/app/admin/**/*.tsx', recursive=True) + ['src/app/admin/page.tsx']
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace literal ₹ with \u20B9
        # But wait, in JSX text nodes, \u20B9 will be printed literally as '\u20B9'
        # e.g. <td>\u20B9 100</td> renders as "\u20B9 100"
        # We need to use {"\u20B9"} for JSX text nodes.
        # It's actually safer to just keep '₹' and ensure the file is UTF-8.
        # But let's check if there are any â‚¹ left.
        content = content.replace('â‚¹', '₹')
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)

make_bulletproof()
