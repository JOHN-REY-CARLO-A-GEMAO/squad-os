import sqlite3
import os

db_paths = ['shared_memory.db', 'instance/shared_memory.db']

for path in db_paths:
    if os.path.exists(path):
        print(f"🔄 Updating {path}...")
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # 1. Ensure the table exists
        cursor.execute('''CREATE TABLE IF NOT EXISTS missions 
                         (id INTEGER PRIMARY KEY, name TEXT, description TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # 2. Add the mission if the table is empty
        cursor.execute("SELECT count(*) FROM missions")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO missions (name, description, status) VALUES (?, ?, ?)",
                           ('SearchDemo', 'Search for AI trends, take screenshot, COMMIT.', 'QUEUED'))
        
        # 3. Retry only failed or errored missions by setting them back to QUEUED
        cursor.execute("UPDATE missions SET status = 'QUEUED' WHERE status IN ('FAILED', 'ERROR')")
        
        conn.commit()
        conn.close()
        print(f"✅ {path} updated successfully!")
    else:
        print(f"ℹ️ {path} not found, skipping.")

print("\n🚀 All databases are synced! Restart your worker now.")