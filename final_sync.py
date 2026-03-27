import sqlite3
import os

# The two potential database locations
db_configs = [
    {
        "path": "shared_memory.db",
        "name_col": "goal",
        "desc_col": None  # Root DB only has 'goal'
    },
    {
        "path": "instance/shared_memory.db",
        "name_col": "name",
        "desc_col": "description"
    }
]

for config in db_configs:
    path = config["path"]
    if os.path.exists(path):
        print(f"🔄 Syncing {path}...")
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # 1. Clear old failed attempts
        cursor.execute("DELETE FROM missions")
        
        # 2. Insert the mission using the correct column for THIS database
        if config["name_col"] == "goal":
            # Root DB Schema: id, goal, status, created_at
            cursor.execute(
                "INSERT INTO missions (goal, status) VALUES (?, ?)",
                ("Search for Agentic OS trends 2026, take a screenshot, and COMMIT it.", "QUEUED")
            )
        else:
            # Instance DB Schema: id, name, description, status, created_at
            cursor.execute(
                "INSERT INTO missions (name, description, status) VALUES (?, ?, ?)",
                ("SearchDemo", "Search for Agentic OS trends 2026 and COMMIT.", "QUEUED")
            )
            
        conn.commit()
        conn.close()
        print(f"✅ {path} is now primed with a QUEUED mission.")
    else:
        print(f"ℹ️ {path} not found.")

print("\n🚀 All databases are synced. Restart your worker now!")