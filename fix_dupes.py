with open("backend/app/api/v1/endpoints/licenses.py", "r", encoding="utf-8") as f:
    content = f.read()

# Just deduplicate the final list
# Wait, let's look at the end of get_telegram_licenses
import re
match = re.search(r'trial_lic_res = await db.execute\(select\(License\).filter\(License.id.in_\(trial_ids\)\)\).*?licenses.extend\(trial_lics\)', content, re.DOTALL)
if match:
    replacement = match.group(0) + "\n    \n    # Deduplicate by ID\n    seen = set()\n    unique_licenses = []\n    for l in licenses:\n        if l.id not in seen:\n            seen.add(l.id)\n            unique_licenses.append(l)\n    licenses = unique_licenses\n"
    content = content.replace(match.group(0), replacement)
    with open("backend/app/api/v1/endpoints/licenses.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added deduplication")
else:
    print("Could not find match")
