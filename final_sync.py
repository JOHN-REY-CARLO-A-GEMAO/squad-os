import argparse
import datetime
import json
import os
import sqlite3

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


def backup_missions(cursor, db_path):
    cursor.execute("SELECT * FROM missions")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    backup_records = [dict(zip(columns, row)) for row in rows]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"missions_backup_{os.path.basename(db_path)}_{timestamp}.json"
    with open(backup_filename, "w", encoding="utf-8") as backup_file:
        json.dump({
            "database": db_path,
            "backup_time": timestamp,
            "rows": backup_records
        }, backup_file, indent=2)
    return backup_filename, [record.get("id") for record in backup_records]


def prompt_confirmation(prompt_text):
    response = input(f"{prompt_text} [y/N]: ").strip().lower()
    return response in ("y", "yes")


def sync_database(config, dry_run=False, assume_yes=False):
    db_path = config["path"]
    if not os.path.exists(db_path):
        print(f"ℹ️ {db_path} not found.")
        return

    print(f"🔄 Syncing {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM missions")
    before_ids = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(before_ids)} existing mission rows.")
    print(f"Mission IDs to delete: {before_ids}")

    if dry_run:
        print("⚠️ Dry run enabled. No changes will be made.")
        conn.close()
        return

    if before_ids and not assume_yes:
        if not prompt_confirmation("Confirm deletion of existing mission rows?"):
            print("⏭️ Skipping deletion for this database.")
            conn.close()
            return

    backup_filename, backup_ids = backup_missions(cursor, db_path)
    print(f"📦 Backed up {len(backup_ids)} mission rows to {backup_filename}")

    try:
        with conn:
            cursor.execute("DELETE FROM missions")
            cursor.execute("SELECT id FROM missions")
            after_ids = [row[0] for row in cursor.fetchall()]
            deleted_ids = [mid for mid in before_ids if mid not in after_ids]
            print(f"Deleted mission IDs: {deleted_ids}")
            print(f"Mission IDs remaining after delete: {after_ids}")

            if config["name_col"] == "goal":
                cursor.execute(
                    "INSERT INTO missions (goal, status) VALUES (?, ?)",
                    ("Search for Agentic OS trends 2026, take a screenshot, and COMMIT it.", "QUEUED")
                )
            else:
                cursor.execute(
                    "INSERT INTO missions (name, description, status) VALUES (?, ?, ?)",
                    ("SearchDemo", "Search for Agentic OS trends 2026 and COMMIT.", "QUEUED")
                )

        print(f"✅ {db_path} is now primed with a QUEUED mission.")
    except Exception as exc:
        conn.rollback()
        print(f"❌ Error while syncing {db_path}: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely sync missions databases.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation and proceed."
    )
    args = parser.parse_args()

    for cfg in db_configs:
        sync_database(cfg, dry_run=args.dry_run, assume_yes=args.yes)

    print("\n🚀 All databases are synced. Restart your worker now!")
