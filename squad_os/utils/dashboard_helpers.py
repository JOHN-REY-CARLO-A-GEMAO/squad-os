import sqlite3
import os
from datetime import datetime


DB_PATHS = ["shared_memory.db", "instance/shared_memory.db"]


def ensure_personas_table():
    for path in DB_PATHS:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_personas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT UNIQUE NOT NULL,
                        goal TEXT NOT NULL,
                        backstory TEXT NOT NULL,
                        tools TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                conn.close()
            except Exception:
                pass


def format_project_label(project_id):
    """Transforms a project ID like '20241027_123456_my_project' into '12:34:56 - My Project'."""
    parts = project_id.split("_")
    if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:
        time_part = parts[1]
        formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        slug_part = " ".join(parts[2:]).title()
        return f"{formatted_time} - {slug_part}"
    return project_id.replace("_", " ").title()


def format_log_timestamp(ts_str):
    """Converts ISO timestamp strings to HH:MM:SS format for cleaner logs."""
    if not ts_str:
        return ""
    try:
        dt = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except Exception:
        return str(ts_str)
