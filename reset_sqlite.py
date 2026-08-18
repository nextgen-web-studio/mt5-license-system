import os

def insert_reset_logic(filepath, table_name, delete_var):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    reset_logic = f'''
    from sqlalchemy import text
    # Reset sqlite_sequence if table is empty
    count_res = await db.execute(text("SELECT COUNT(*) FROM {table_name}"))
    if count_res.scalar() == 0:
        await db.execute(text("DELETE FROM sqlite_sequence WHERE name='{table_name}'"))
    else:
        max_res = await db.execute(text("SELECT MAX(id) FROM {table_name}"))
        max_id = max_res.scalar() or 0
        await db.execute(text(f"UPDATE sqlite_sequence SET seq = {{max_id}} WHERE name='{table_name}'"))
    await db.commit()
'''
    
    if 'DELETE FROM sqlite_sequence' not in content:
        # replace the original delete call with the delete + reset
        target = f'await db.delete({delete_var})\n    await db.commit()'
        replacement = target + reset_logic
        content = content.replace(target, replacement)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

insert_reset_logic('backend/app/api/v1/endpoints/orders.py', 'orders', 'order')
insert_reset_logic('backend/app/api/v1/endpoints/licenses.py', 'licenses', 'license_obj')
