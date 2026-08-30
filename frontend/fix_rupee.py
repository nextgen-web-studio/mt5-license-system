import glob
import re

def fix_rupee_symbol():
    files = glob.glob('src/app/admin/**/*.tsx', recursive=True)
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # The file might contain literal ₹ or mangled text like â‚¹
        # We can use regex to replace anything resembling the mangled ruin or actual rupee
        # Actually, let's just do a direct replace of the specific lines or known bad characters.
        # Mangled variants: â‚¹, ,1, or literal ₹
        
        # Replace literal ₹
        content = content.replace('₹', '&#8377;')
        
        # Replace known mangled UTF-8 in windows-1252: â‚¹
        content = content.replace('â‚¹', '&#8377;')
        
        # Another common mangling is when '₹' gets decoded badly.
        # Let's also just search for "Amount (â‚¹)" and replace it.
        content = content.replace('Amount (â‚¹)', 'Amount (&#8377;)')
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Processed {file}")

fix_rupee_symbol()
