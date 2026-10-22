import sqlite3

conn = sqlite3.connect("smartattend.db")
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for (name,) in rows:
    print(name)
conn.close()