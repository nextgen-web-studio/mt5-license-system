import glob

def speed_up_polling():
    files = glob.glob('src/app/admin/**/*.tsx', recursive=True) + ['src/app/admin/page.tsx']
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'refetchInterval: 10000' in content:
            content = content.replace('refetchInterval: 10000', 'refetchInterval: 2000')
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {file}")

speed_up_polling()
