import sqlite3

conn = sqlite3.connect("infinity_trading.db")
c = conn.cursor()
try:
    c.execute("ALTER TABLE orders ADD COLUMN vps_id INTEGER REFERENCES vps_orders(id);")
    conn.commit()
    print("Migration successful")
except Exception as e:
    print("Error:", e)
conn.close()
