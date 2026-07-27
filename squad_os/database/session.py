import os
import sqlite3
import aiosqlite
import json
import asyncio
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

TASKS_COLUMNS = {
    "verification_status": "ALTER TABLE tasks ADD COLUMN verification_status TEXT",
    "verification_details": "ALTER TABLE tasks ADD COLUMN verification_details TEXT",
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

    cursor = await db.execute("PRAGMA table_info(tasks)")
    existing_tasks = {row[1] for row in await cursor.fetchall()}

    for col, alter_sql in TASKS_COLUMNS.items():
        if col not in existing_tasks:
            try:
                await db.execute(alter_sql)
                print(f"[DB Migration] Added column '{col}' to tasks table.")
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

        # 10. Mobile Remote Companion Tables (v1.0 Architecture Blueprint)
        # workspaces table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                goal TEXT,
                system_prompt TEXT,
                active_model TEXT DEFAULT 'claude-3-5-sonnet',
                temperature REAL DEFAULT 0.2,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_workspace_id ON conversations(workspace_id)")

        # conversation_memories table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_conv_memory_key ON conversation_memories(conversation_id, memory_key)")

        # conversation_events table (Immutable Event-Sourcing Timeline with parent nesting)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_event_id INTEGER,
                conversation_id INTEGER NOT NULL,
                sequence_id INTEGER NOT NULL,
                event_namespace TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                mission_id INTEGER,
                payload_schema_version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_event_id) REFERENCES conversation_events(id) ON DELETE CASCADE,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
            )
        """)
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_sequence_id ON conversation_events(sequence_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_conversation_id ON conversation_events(conversation_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_parent_id ON conversation_events(parent_event_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_mission_id ON conversation_events(mission_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_namespace_type ON conversation_events(event_namespace, event_type)")

        # mission_snapshots table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mission_snapshots (
                mission_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                latest_thought TEXT,
                next_action TEXT,
                eta INTEGER DEFAULT 0,
                confidence TEXT DEFAULT 'HIGH',
                token_usage INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
            )
        """)

        # devices table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default_user',
                push_token TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL,
                device_model TEXT,
                is_active INTEGER DEFAULT 1,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # system_notifications table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                deep_link TEXT,
                status TEXT DEFAULT 'PENDING',
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
        """)

        # Seeding logic: Default workspace & conversation
        cursor = await db.execute("SELECT COUNT(*) FROM workspaces")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.execute(
                "INSERT INTO workspaces (name, description) VALUES (?, ?)",
                ("Squad OS Workspace", "Default workspace for the Squad OS Companion App")
            )
            # Fetch the workspace ID
            cursor = await db.execute("SELECT id FROM workspaces WHERE name = ?", ("Squad OS Workspace",))
            workspace_id = (await cursor.fetchone())[0]

            await db.execute(
                "INSERT INTO conversations (workspace_id, title, summary, goal, system_prompt, active_model, temperature) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (workspace_id, "JWT Auth Migration", "Refactoring outdated authentication handlers in secure modules", "Introduce robust refresh-token rotation", "You are a senior security engineer specializing in Flutter and Supabase.", "claude-3-5-sonnet", 0.2)
            )
            # Let's seed initial conversation memories
            cursor = await db.execute("SELECT id FROM conversations LIMIT 1")
            conv_id = (await cursor.fetchone())[0]
            await db.execute(
                "INSERT INTO conversation_memories (conversation_id, memory_key, memory_value) VALUES (?, ?, ?)",
                (conv_id, "framework", "Flutter")
            )
            await db.execute(
                "INSERT INTO conversation_memories (conversation_id, memory_key, memory_value) VALUES (?, ?, ?)",
                (conv_id, "branch", "feature/jwt-refresh")
            )
            await db.execute(
                "INSERT INTO conversation_memories (conversation_id, memory_key, memory_value) VALUES (?, ?, ?)",
                (conv_id, "environment", "Supabase Production")
            )
            await db.execute(
                "INSERT INTO conversation_memories (conversation_id, memory_key, memory_value) VALUES (?, ?, ?)",
                (conv_id, "constraints", "Do not use legacy provider classes. Use modern Riverpod structures.")
            )

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


async def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
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
        "created_at", "verification_status", "verification_details"
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

async def get_task_interrupt(mission_id: int, task_idx: int) -> Optional[Dict[str, Any]]:
    """Return the latest interrupt for a given mission+task, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mission_interrupts WHERE mission_id = ? AND task_idx = ? ORDER BY id DESC LIMIT 1",
            (mission_id, task_idx)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

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


# --- MOBILE REMOTE COMPANION HELPERS ---

async def create_workspace(name: str, description: Optional[str] = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO workspaces (name, description) VALUES (?, ?)",
            (name, description)
        )
        await db.commit()
        return cursor.lastrowid

async def get_workspaces() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM workspaces ORDER BY id ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def create_conversation(
    workspace_id: int,
    title: str,
    summary: Optional[str] = None,
    goal: Optional[str] = None,
    system_prompt: Optional[str] = None,
    active_model: str = "claude-3-5-sonnet",
    temperature: float = 0.2
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (workspace_id, title, summary, goal, system_prompt, active_model, temperature) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (workspace_id, title, summary, goal, system_prompt, active_model, temperature)
        )
        await db.commit()
        return cursor.lastrowid

async def get_conversations(workspace_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM conversations WHERE workspace_id = ? ORDER BY id ASC",
            (workspace_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_conversation_by_id(conversation_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_conversation_memory(conversation_id: int) -> Dict[str, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT memory_key, memory_value FROM conversation_memories WHERE conversation_id = ?",
            (conversation_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def update_conversation_memory_fields(conversation_id: int, memories: Dict[str, str]):
    async with aiosqlite.connect(DB_PATH) as db:
        for k, v in memories.items():
            await db.execute(
                """
                INSERT INTO conversation_memories (conversation_id, memory_key, memory_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(conversation_id, memory_key) DO UPDATE SET memory_value = excluded.memory_value, updated_at = CURRENT_TIMESTAMP
                """,
                (conversation_id, k, v)
            )
        await db.commit()

_event_lock = asyncio.Lock()
_broadcast_callbacks = []

def register_broadcast_callback(callback):
    _broadcast_callbacks.append(callback)

async def append_conversation_event(
    conversation_id: int,
    event_namespace: str,
    event_type: str,
    payload: Dict[str, Any],
    parent_event_id: Optional[int] = None,
    mission_id: Optional[int] = None,
    payload_schema_version: int = 1
) -> int:
    async with _event_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get next monotonic sequence_id
            cursor = await db.execute("SELECT COALESCE(MAX(sequence_id), 0) + 1 FROM conversation_events")
            sequence_id = (await cursor.fetchone())[0]

            cursor = await db.execute(
                """
                INSERT INTO conversation_events
                (parent_event_id, conversation_id, sequence_id, event_namespace, event_type, payload_json, mission_id, payload_schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parent_event_id,
                    conversation_id,
                    sequence_id,
                    event_namespace,
                    event_type,
                    json.dumps(payload),
                    mission_id,
                    payload_schema_version
                )
            )
            await db.commit()
            event_id = cursor.lastrowid

            # Trigger callbacks
            event_data = {
                "id": event_id,
                "parent_event_id": parent_event_id,
                "sequence_id": sequence_id,
                "event_namespace": event_namespace,
                "event_type": event_type,
                "payload_schema_version": payload_schema_version,
                "mission_id": mission_id,
                "payload": payload
            }
            for cb in _broadcast_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(conversation_id, {"type": "EVENT", "data": event_data})
                    else:
                        cb(conversation_id, {"type": "EVENT", "data": event_data})
                except Exception:
                    pass

            return event_id

async def get_conversation_events(conversation_id: int, limit: int = 50, parent_only: bool = False, since_sequence_id: Optional[int] = None) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM conversation_events WHERE conversation_id = ?"
        params = [conversation_id]

        if parent_only:
            query += " AND parent_event_id IS NULL"

        if since_sequence_id is not None:
            query += " AND sequence_id > ?"
            params.append(since_sequence_id)

        query += " ORDER BY sequence_id ASC LIMIT ?"
        params.append(limit)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_mission_snapshot(mission_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mission_snapshots WHERE mission_id = ?", (mission_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_mission_snapshot(
    mission_id: int,
    status: str,
    progress: float,
    latest_thought: Optional[str] = None,
    next_action: Optional[str] = None,
    eta: int = 0,
    confidence: str = "HIGH",
    token_usage: int = 0,
    estimated_cost: float = 0.0
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO mission_snapshots
            (mission_id, status, progress, latest_thought, next_action, eta, confidence, token_usage, estimated_cost, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(mission_id) DO UPDATE SET
                status = excluded.status,
                progress = excluded.progress,
                latest_thought = excluded.latest_thought,
                next_action = excluded.next_action,
                eta = excluded.eta,
                confidence = excluded.confidence,
                token_usage = excluded.token_usage,
                estimated_cost = excluded.estimated_cost,
                last_updated = CURRENT_TIMESTAMP
            """,
            (
                mission_id,
                status,
                progress,
                latest_thought,
                next_action,
                eta,
                confidence,
                token_usage,
                estimated_cost
            )
        )
        await db.commit()

        # Trigger callbacks
        snapshot_data = {
            "event_namespace": "MISSION",
            "event_type": "SNAPSHOT_UPDATE",
            "payload_schema_version": 1,
            "payload": {
                "mission_id": mission_id,
                "status": status,
                "progress": progress,
                "eta": eta,
                "latest_thought": latest_thought,
                "next_action": next_action,
                "confidence": confidence,
                "token_usage": token_usage,
                "estimated_cost": estimated_cost
            }
        }
        for cb in _broadcast_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(1, snapshot_data) # Default conversation_id = 1
                else:
                    cb(1, snapshot_data)
            except Exception:
                pass

async def register_device(
    push_token: str,
    platform: str,
    device_model: Optional[str] = None,
    user_id: str = "default_user"
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO devices (push_token, platform, device_model, user_id, is_active, last_seen_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(push_token) DO UPDATE SET
                is_active = 1,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (push_token, platform, device_model, user_id)
        )
        await db.commit()
        cursor = await db.execute("SELECT id FROM devices WHERE push_token = ?", (push_token,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_active_devices() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM devices WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def revoke_device(device_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE devices SET is_active = 0 WHERE id = ?", (device_id,))
        await db.commit()

async def search_conversation_events(conversation_id: int, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        search_query = f"%{query}%"
        async with db.execute(
            """
            SELECT id, event_namespace, event_type, payload_json, created_at
            FROM conversation_events
            WHERE conversation_id = ? AND (payload_json LIKE ? OR event_type LIKE ?)
            ORDER BY sequence_id DESC LIMIT ?
            """,
            (conversation_id, search_query, search_query, limit)
         ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]