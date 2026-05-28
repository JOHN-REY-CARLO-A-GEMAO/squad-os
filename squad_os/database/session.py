import os
import sqlite3
import aiosqlite
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

DB_PATH = "shared_memory.db"

# --- STATUS ENUMS ---
class MissionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUEUED = "QUEUED"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

# --- PYDANTIC MODELS ---

class MissionRecord(BaseModel):
    id: Optional[int] = None
    goal: str
    status: str = MissionStatus.PENDING.value
    uploaded_files: Optional[str] = None  # JSON string containing file metadata
    workflow_json: Optional[str] = None  # JSON string containing pre-built workflow DAG
    conversation_history: str = "[]"  # JSON array of follow-up messages
    created_at: datetime = Field(default_factory=datetime.now)

class TaskRecord(BaseModel):
    id: Optional[int] = None
    mission_id: int
    description: str
    assigned_agent: str
    status: str = TaskStatus.PENDING.value
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    execution_ms: int = 0
    retry_count: int = 0
    created_at: Optional[datetime] = None

class ApprovalRecord(BaseModel):
    id: Optional[int] = None
    task_id: int
    mission_id: int
    message: str
    status: str = ApprovalStatus.PENDING.value
    feedback: Optional[str] = None

class AgentPersona(BaseModel):
    id: Optional[int] = None
    role: str
    goal: str
    backstory: str
    tools: str  # JSON string list of tool names
    created_at: Optional[datetime] = None

# --- DATABASE INITIALIZATION ---

MISSIONS_COLUMNS = {
    "uploaded_files": "ALTER TABLE missions ADD COLUMN uploaded_files TEXT",
    "workflow_json": "ALTER TABLE missions ADD COLUMN workflow_json TEXT",
    "conversation_history": "ALTER TABLE missions ADD COLUMN conversation_history TEXT DEFAULT '[]'",
}


async def _run_migrations(db: aiosqlite.Connection):
    """Detect missing columns on existing tables and add them."""
    cursor = await db.execute("PRAGMA table_info(missions)")
    existing = {row[1] for row in await cursor.fetchall()}

    for col, alter_sql in MISSIONS_COLUMNS.items():
        if col not in existing:
            try:
                await db.execute(alter_sql)
                print(f"[DB Migration] Added column '{col}' to missions table.")
            except aiosqlite.Error as e:
                print(f"[DB Migration] Note: Could not add '{col}': {e}")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        
        # 1. Missions Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT NOT NULL,
                uploaded_files TEXT,
                workflow_json TEXT,
                conversation_history TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # MIGRATION: Auto-detect missing columns and add them
        await _run_migrations(db)

        # 2. Tasks Table
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            )
        """)

        # 3. Approvals Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                mission_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            )
        """)

        # 4. NEW: Global Blackboard (Shared State between Agents)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blackboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Schedule Tables (for cron-like scheduling)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_goal TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                schedule_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                mission_id INTEGER,
                metadata TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedule_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER,
                mission_id INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                output TEXT,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id)
            )
        """)

        # 6. HITL Recovery Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mission_interrupts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                task_idx INTEGER,
                context TEXT,
                error_message TEXT,
                user_guidance TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id) ON DELETE CASCADE
            )
        """)
        # 7. Agent Personas Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT UNIQUE NOT NULL,
                goal TEXT NOT NULL,
                backstory TEXT NOT NULL,
                tools TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. Agent Store Tables (for .sqad package ecosystem)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS store_packages (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                author TEXT,
                description TEXT,
                min_squad_os_version TEXT,
                tags TEXT,
                source_url TEXT,
                install_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS installed_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id TEXT NOT NULL,
                version TEXT NOT NULL,
                install_path TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (package_id) REFERENCES store_packages(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS store_tools (
                id TEXT PRIMARY KEY,
                package_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                parameters TEXT,
                entry_point TEXT,
                dependencies TEXT,
                FOREIGN KEY (package_id) REFERENCES store_packages(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS store_workflows (
                id TEXT PRIMARY KEY,
                package_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                workflow TEXT NOT NULL,
                FOREIGN KEY (package_id) REFERENCES store_packages(id)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_installed_packages_package_id ON installed_packages(package_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_store_tools_package_id ON store_tools(package_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_store_workflows_package_id ON store_workflows(package_id)")

        # 9. Performance Indexes
        # Optimizes mission retrieval by status (e.g. Dashboard, Worker Queue)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status)")
        # Optimizes task lookups for specific missions (Mission View, Context Loading)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_mission_id ON tasks(mission_id)")
        # Optimizes task filtering by status
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        # Optimizes approval retrieval for missions
        await db.execute("CREATE INDEX IF NOT EXISTS idx_approvals_mission_id ON approvals(mission_id)")
        # Optimizes interrupt retrieval for missions
        await db.execute("CREATE INDEX IF NOT EXISTS idx_interrupts_mission_id ON mission_interrupts(mission_id)")
        # Optimizes persona lookups by role
        await db.execute("CREATE INDEX IF NOT EXISTS idx_personas_role ON agent_personas(role)")

        await db.commit()

async def init_interrupts_table():
    """Create the mission_interrupts table if it doesn't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mission_interrupts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                task_idx INTEGER,
                context TEXT,
                error_message TEXT,
                user_guidance TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id) ON DELETE CASCADE
            )
        """)
        # Optimize interrupt lookups
        await db.execute("CREATE INDEX IF NOT EXISTS idx_interrupts_mission_id ON mission_interrupts(mission_id)")
        await db.commit()

# --- MISSION & TASK HELPERS ---

async def create_mission(goal: str, uploaded_files: Optional[str] = None, workflow_json: Optional[str] = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO missions (goal, status, uploaded_files, workflow_json) VALUES (?, ?, ?, ?)",
            (goal, MissionStatus.IN_PROGRESS.value, uploaded_files, workflow_json)
        )
        await db.commit()
        return cursor.lastrowid

async def append_conversation(mission_id: int, role: str, content: str):
    """Append a message to a mission's conversation_history."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT conversation_history FROM missions WHERE id = ?", (mission_id,))
        row = await cursor.fetchone()
        if not row:
            return
        history = json.loads(row[0] or "[]")
        history.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat() + "Z"})
        await db.execute("UPDATE missions SET conversation_history = ? WHERE id = ?", (json.dumps(history), mission_id))
        await db.commit()


async def get_conversation(mission_id: int) -> list:
    """Get the full conversation history for a mission."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT conversation_history FROM missions WHERE id = ?", (mission_id,))
        row = await cursor.fetchone()
        if not row:
            return []
        return json.loads(row[0] or "[]")


async def set_mission_status(mission_id: int, status: str):
    """Update a mission's status."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE missions SET status = ? WHERE id = ?", (status, mission_id))
        await db.commit()


async def get_mission(mission_id: int) -> Optional[Dict[str, Any]]:
    """Get a mission's full row as a dict."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)


async def get_next_followup_mission() -> Optional[Dict[str, Any]]:
    """Get the next mission awaiting a follow-up (status='FOLLOWUP'), ordered by oldest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM missions WHERE status = 'FOLLOWUP' ORDER BY id ASC LIMIT 1"
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)


async def get_mission(mission_id: int) -> Optional[Dict[str, Any]]:
    """Get a mission's full row as a dict."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)


async def create_task(mission_id: int, description: str, assigned_agent: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (mission_id, description, assigned_agent, status) VALUES (?, ?, ?, ?)",
            (mission_id, description, assigned_agent, TaskStatus.PENDING.value)
        )
        await db.commit()
        return cursor.lastrowid

async def update_task(task_id: int, **kwargs):
    allowed_columns = {
        "mission_id", "description", "assigned_agent", "status",
        "input_data", "output_data", "error", "prompt_tokens",
        "completion_tokens", "cost_usd", "execution_ms", "retry_count",
        "created_at"
    }
    invalid_keys = [k for k in kwargs.keys() if k not in allowed_columns]
    if invalid_keys:
        raise ValueError(f"Invalid task column(s): {', '.join(invalid_keys)}")
    if not kwargs:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        keys = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [task_id]
        await db.execute(f"UPDATE tasks SET {keys} WHERE id = ?", values)
        await db.commit()

async def update_mission(mission_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE missions SET status = ? WHERE id = ?", (status, mission_id))
        await db.commit()

# --- DASHBOARD & INTERACTIVITY HELPERS ---

async def create_approval_request(mission_id: int, task_id: int, message: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO approvals (mission_id, task_id, message, status) VALUES (?, ?, ?, ?)",
            (mission_id, task_id, message, ApprovalStatus.PENDING.value)
        )
        await db.commit()
        return cursor.lastrowid

async def get_approval_status(approval_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT status, feedback FROM approvals WHERE id = ?", (approval_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

# --- QUEUE & MEMORY HELPERS ---

async def search_past_memory(query: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Use trailing wildcard only for better index utilization
        # Leading % forces full table scan which is inefficient
        search_query = f"{query}%"
        async with db.execute(
            "SELECT assigned_agent, output_data, created_at FROM tasks "
            "WHERE status = ? AND output_data LIKE ? "
            "ORDER BY id DESC LIMIT 5",
            (TaskStatus.COMPLETED.value, search_query)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def add_to_queue(goal: str, uploaded_files: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO missions (goal, status, uploaded_files) VALUES (?, ?, ?)",
            (goal, MissionStatus.QUEUED.value, uploaded_files)
        )
        await db.commit()

async def get_next_queued_mission():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM missions WHERE status = ? ORDER BY id ASC LIMIT 1",
            (MissionStatus.QUEUED.value,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

# --- NEW: BLACKBOARD HELPERS (Agent-to-Agent Communication) ---

async def update_blackboard(key: str, value: str):
    """Save or update a piece of shared information."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO blackboard (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", 
            (key, value)
        )
        await db.commit()

async def read_blackboard(key: str):
    """Retrieve shared information by key."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM blackboard WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# --- HITL INTERRUPT HELPERS ---

async def create_interrupt(mission_id: int, task_idx: Optional[int] = None, context: Optional[str] = None, error_message: Optional[str] = None) -> int:
    """Create a new PENDING interrupt for a mission. Returns the new interrupt id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO mission_interrupts (mission_id, task_idx, context, error_message, status) VALUES (?, ?, ?, ?, 'PENDING')",
            (mission_id, task_idx, context, error_message)
        )
        await db.commit()
        return cursor.lastrowid

async def get_pending_interrupt(mission_id: int) -> Optional[Dict[str, Any]]:
    """Return the oldest PENDING interrupt for the given mission_id, or None if no pending interrupt exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mission_interrupts WHERE mission_id = ? AND status = 'PENDING' ORDER BY id ASC LIMIT 1",
            (mission_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_interrupt_guidance(interrupt_id: int, user_guidance: str):
    """Store user guidance for an interrupt and mark it RESOLVED."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE mission_interrupts SET user_guidance = ?, status = 'RESOLVED' WHERE id = ?",
            (user_guidance, interrupt_id)
        )
        await db.commit()

# --- AGENT PERSONA HELPERS ---

async def save_persona(role: str, goal: str, backstory: str, tools: List[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO agent_personas (role, goal, backstory, tools) VALUES (?, ?, ?, ?)",
            (role, goal, backstory, json.dumps(tools))
        )
        await db.commit()

async def get_all_personas() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM agent_personas ORDER BY role ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_persona_by_role(role: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM agent_personas WHERE role = ?", (role,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_persona(role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM agent_personas WHERE role = ?", (role,))
        await db.commit()