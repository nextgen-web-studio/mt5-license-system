import glob

def fix_rupee_again():
    files = glob.glob('src/app/admin/**/*.tsx', recursive=True)
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace &#8377; with ₹ but ensure we save file as UTF-8 with BOM?
        # Actually, if we just use {"\u20B9"} in JSX text nodes, and \u20B9 in strings.
        # Let's just use the actual character '₹' and encode it strictly as utf-8.
        # The previous issue was probably that someone opened the file in notepad or another editor and saved it as ANSI/Windows-1252.
        # We will replace &#8377; with '₹' and save it carefully.
        content = content.replace('&#8377;', '₹')
        content = content.replace(',1', '₹')  # Another common mangled string in the PS output
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Processed {file}")

fix_rupee_again()
