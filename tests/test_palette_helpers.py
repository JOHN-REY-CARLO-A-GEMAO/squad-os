import os
import sqlite3
import pytest
from squad_os.utils.dashboard_helpers import format_project_label, format_log_timestamp, ensure_personas_table, DB_PATHS

def test_format_project_label():
    # Standard format
    assert format_project_label("20241027_123456_my_project") == "12:34:56 - My Project"
    # Long slug
    assert format_project_label("20241027_123456_my_long_project_name") == "12:34:56 - My Long Project Name"
    # Non-standard format
    assert format_project_label("old_project_style") == "Old Project Style"
    assert format_project_label("simple") == "Simple"
    # Edge cases
    assert format_project_label("") == ""
    assert format_project_label("20241027_") == "20241027 "
    assert format_project_label("20241027_000000_o") == "00:00:00 - O"

def test_format_log_timestamp():
    # ISO format
    assert format_log_timestamp("2024-10-27T12:34:56.789Z") == "12:34:56"
    assert format_log_timestamp("2024-10-27T15:00:00") == "15:00:00"
    # Invalid format
    assert format_log_timestamp("not-a-date") == "not-a-date"
    # None/Empty
    assert format_log_timestamp(None) == ""
    assert format_log_timestamp("") == ""

def test_ensure_personas_table_creates_table(monkeypatch):
    db_path = "test_palette_personas.db"
    monkeypatch.setattr("squad_os.utils.dashboard_helpers.DB_PATHS", [db_path])
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE missions (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        ensure_personas_table()

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_personas'")
        assert cursor.fetchone() is not None
        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_ensure_personas_table_idempotent(monkeypatch):
    db_path = "test_palette_idempotent.db"
    monkeypatch.setattr("squad_os.utils.dashboard_helpers.DB_PATHS", [db_path])
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE missions (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        ensure_personas_table()
        ensure_personas_table()

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='agent_personas'")
        assert cursor.fetchone()[0] == 1
        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
