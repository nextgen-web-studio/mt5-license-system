import os
import glob

# Replace all toLocaleString() with a consistent explicit format
files = glob.glob('frontend/src/app/admin/**/*.tsx', recursive=True)

fix1 = ".toLocaleString()"
fix2 = ".toLocaleDateString()"
replacement = ".toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })"

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    original = content
    content = content.replace(fix1, replacement)
    content = content.replace(fix2, replacement)

    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'Updated: {f}')

print('Done')
