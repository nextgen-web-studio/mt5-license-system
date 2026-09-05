with open("backend/app/api/v1/endpoints/licenses.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """        trial_lic_res = await db.execute(select(License).filter(License.id.in_(trial_ids)))
        licenses.extend(trial_lic_res.scalars().all())
        
    return licenses"""

replacement = """        trial_lic_res = await db.execute(select(License).filter(License.id.in_(trial_ids)))
        licenses.extend(trial_lic_res.scalars().all())
        
    # Deduplicate by ID
    seen = set()
    unique_licenses = []
    for l in licenses:
        if l.id not in seen:
            seen.add(l.id)
            unique_licenses.append(l)
    
    return unique_licenses"""

content = content.replace(target, replacement)

with open("backend/app/api/v1/endpoints/licenses.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Added deduplication")
