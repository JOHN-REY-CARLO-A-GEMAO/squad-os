"""Blackboard / personas / conversations / events persistence.

Split from session.py (PR4). Move-only: no logic changes.
Imports DB_PATH + event-bus infra from session_missions (one direction,
no cycles).
"""

import aiosqlite
import asyncio
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from squad_os.database.session_missions import (
    DB_PATH,
    _event_lock,
    _broadcast_callbacks,
)

class AgentPersona(BaseModel):
    id: Optional[int] = None
    role: str
    goal: str
    backstory: str
    tools: str  # JSON string list of tool names
    created_at: Optional[str] = None

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
