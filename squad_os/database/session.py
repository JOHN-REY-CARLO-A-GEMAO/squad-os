import os
import sqlite3
import aiosqlite
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

DB_PATH = "shared_memory.db"

class MissionRecord(BaseModel):
    id: Optional[int] = None
    goal: str
    status: str = "PENDING"
    created_at: datetime = datetime.now()

class TaskRecord(BaseModel):
    id: Optional[int] = None
    mission_id: int
    description: str
    assigned_agent: str
    status: str = "PENDING"
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    execution_ms: int = 0
    retry_count: int = 0

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                assigned_agent TEXT NOT NULL,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                error TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                execution_ms INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            )
        """)
        await db.commit()

async def create_mission(goal: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO missions (goal, status) VALUES (?, ?)",
            (goal, "IN_PROGRESS")
        )
        await db.commit()
        return cursor.lastrowid

async def create_task(mission_id: int, description: str, assigned_agent: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (mission_id, description, assigned_agent, status) VALUES (?, ?, ?, ?)",
            (mission_id, description, assigned_agent, "PENDING")
        )
        await db.commit()
        return cursor.lastrowid

async def update_task(task_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        keys = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [task_id]
        await db.execute(f"UPDATE tasks SET {keys} WHERE id = ?", values)
        await db.commit()

async def get_mission_tasks(mission_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE mission_id = ?", (mission_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_mission(mission_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE missions SET status = ? WHERE id = ?", (status, mission_id))
        await db.commit()
