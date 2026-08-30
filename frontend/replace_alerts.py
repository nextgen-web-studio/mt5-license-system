import glob
import re

def replace_alerts():
    files = glob.glob('src/app/admin/**/*.tsx', recursive=True)
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'alert(' in content:
            # Add useToast import if not present
            if 'useToast' not in content:
                content = content.replace("import api from '@/lib/api';", "import api from '@/lib/api';\nimport { useToast } from '@/app/providers';")
                
            # Add const { toast } = useToast(); inside component
            # We'll just find the first "export default function" or "const" and insert it
            # Actually, regex is better
            if 'const { toast } = useToast();' not in content:
                # Find the main component body
                content = re.sub(r'(export default function [a-zA-Z0-9_]+\(\) \{)', r'\1\n  const { toast } = useToast();', content)
                
            # Replace alert(something) with toast(something, 'error') or 'success' if it says success
            # Simple approach: replace alert( with toast(
            # But wait, toast takes 2 args. Let's just do toast(something) which defaults to info.
            # But we can replace alert('Failed with toast('Failed', 'error')
            def alert_replacer(match):
                msg = match.group(1)
                # If msg contains 'Failed' or 'error' make it an error
                if 'fail' in msg.lower() or 'error' in msg.lower():
                    return f"toast({msg}, 'error')"
                elif 'success' in msg.lower() or 'sent' in msg.lower():
                    return f"toast({msg}, 'success')"
                return f"toast({msg}, 'info')"
                
            content = re.sub(r'alert\((.*?)\)', alert_replacer, content)
            
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Replaced alerts in {file}")

replace_alerts()
