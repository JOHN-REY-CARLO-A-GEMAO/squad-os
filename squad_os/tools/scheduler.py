"""
SchedulerTool — cron-like scheduling for missions and tasks.

Supports:
- One-time scheduled missions
- Recurring missions (cron syntax)
- Mission queues with execution times
- Schedule management (list, cancel, modify)
"""
import asyncio
import json
import os
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from squad_os.tools.base import BaseTool
from squad_os.database.session import DB_PATH


class ScheduleManager:
    """Manages scheduled missions and recurring tasks."""
    
    @staticmethod
    async def init_db():
        """Initialize schedule tables."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_goal TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,  -- 'once', 'cron', 'interval'
                    schedule_value TEXT NOT NULL,  -- ISO datetime, cron expression, or interval seconds
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE, PAUSED, COMPLETED, CANCELLED
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
            await db.commit()
    
    @staticmethod
    async def add_schedule(
        mission_goal: str,
        schedule_type: str,
        schedule_value: str,
        metadata: Optional[str] = None
    ) -> int:
        """Add a new schedule. Returns schedule ID."""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO schedules (mission_goal, schedule_type, schedule_value, metadata, next_run)
                VALUES (?, ?, ?, ?, ?)
                """,
                (mission_goal, schedule_type, schedule_value, metadata, ScheduleManager._calculate_next_run(schedule_type, schedule_value))
            )
            await db.commit()
            return cursor.lastrowid
    
    @staticmethod
    async def list_schedules(status: Optional[str] = None) -> List[Dict]:
        """List all schedules, optionally filtered by status."""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute("SELECT * FROM schedules WHERE status = ?", (status,))
            else:
                cursor = await db.execute("SELECT * FROM schedules")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
    
    @staticmethod
    async def cancel_schedule(schedule_id: int) -> bool:
        """Cancel a schedule."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE schedules SET status = 'CANCELLED' WHERE id = ?", (schedule_id,))
            await db.commit()
            return True
    
    @staticmethod
    async def pause_schedule(schedule_id: int) -> bool:
        """Pause a schedule."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE schedules SET status = 'PAUSED' WHERE id = ?", (schedule_id,))
            await db.commit()
            return True
    
    @staticmethod
    async def resume_schedule(schedule_id: int) -> bool:
        """Resume a paused schedule."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE schedules SET status = 'ACTIVE' WHERE id = ?", (schedule_id,))
            await db.commit()
            return True
    
    @staticmethod
    async def get_due_schedules() -> List[Dict]:
        """Get schedules that are due for execution."""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM schedules WHERE status = 'ACTIVE' AND next_run <= ?",
                (now,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
    
    @staticmethod
    async def update_schedule_after_run(schedule_id: int, mission_id: int, status: str):
        """Update schedule after a mission run."""
        async with aiosqlite.connect(DB_PATH) as db:
            # Get schedule info
            cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
            schedule = await cursor.fetchone()
            if not schedule:
                return
            
            # Update last_run and next_run
            next_run = ScheduleManager._calculate_next_run(schedule[3], schedule[4])
            await db.execute(
                """
                UPDATE schedules 
                SET last_run = CURRENT_TIMESTAMP, next_run = ?, mission_id = ?
                WHERE id = ?
                """,
                (next_run, mission_id, schedule_id)
            )
            
            # Log to history
            await db.execute(
                """
                INSERT INTO schedule_history (schedule_id, mission_id, status)
                VALUES (?, ?, ?)
                """,
                (schedule_id, mission_id, status)
            )
            
            await db.commit()
    
    @staticmethod
    def _calculate_next_run(schedule_type: str, schedule_value: str) -> Optional[str]:
        """Calculate next run time based on schedule type and value."""
        now = datetime.now()
        
        if schedule_type == "once":
            return schedule_value  # ISO datetime string
        
        elif schedule_type == "interval":
            try:
                seconds = int(schedule_value)
                next_time = now + timedelta(seconds=seconds)
                return next_time.isoformat()
            except ValueError:
                return None
        
        elif schedule_type == "cron":
            # Simplified cron: "minute hour day month weekday"
            # For now, support basic intervals like "every hour", "every day"
            parts = schedule_value.lower().split()
            if len(parts) >= 2:
                minute, hour = parts[0], parts[1]
                next_time = now.replace(minute=int(minute) if minute != "*" else 0, 
                                       hour=int(hour) if hour != "*" else 0,
                                       second=0, microsecond=0)
                if next_time <= now:
                    next_time += timedelta(days=1)
                return next_time.isoformat()
        
        return None


class ScheduleMissionTool(BaseTool):
    name = "schedule_mission"
    description = (
        "Schedule a mission to run at a specific time or on a recurring basis. "
        "Supports one-time schedules, intervals (in seconds), and cron-like expressions. "
        "Returns the schedule ID for future reference."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mission_goal": {
                "type": "string",
                "description": "The mission goal/description to schedule"
            },
            "schedule_type": {
                "type": "string",
                "enum": ["once", "interval", "cron"],
                "description": "Type of schedule: 'once' (single run), 'interval' (recurring seconds), 'cron' (cron expression)"
            },
            "schedule_value": {
                "type": "string",
                "description": "Schedule value: ISO datetime for 'once', seconds for 'interval', cron expression for 'cron'"
            },
            "metadata": {
                "type": "string",
                "description": "Optional metadata (JSON string) for the schedule"
            }
        },
        "required": ["mission_goal", "schedule_type", "schedule_value"]
    }
    category = "scheduling"

    async def execute(
        self,
        mission_goal: str,
        schedule_type: str,
        schedule_value: str,
        metadata: Optional[str] = None
    ) -> str:
        try:
            schedule_id = await ScheduleManager.add_schedule(
                mission_goal, schedule_type, schedule_value, metadata
            )
            next_run = ScheduleManager._calculate_next_run(schedule_type, schedule_value)
            return f"Schedule created (ID: {schedule_id}). Next run: {next_run}. Mission: {mission_goal}"
        except Exception as e:
            return f"Error creating schedule: {e}"


class ListSchedulesTool(BaseTool):
    name = "list_schedules"
    description = (
        "List all scheduled missions. Optionally filter by status (ACTIVE, PAUSED, CANCELLED, COMPLETED)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["ACTIVE", "PAUSED", "CANCELLED", "COMPLETED"],
                "description": "Filter by schedule status (optional)"
            }
        },
        "required": []
    }
    category = "scheduling"

    async def execute(self, status: Optional[str] = None) -> str:
        try:
            schedules = await ScheduleManager.list_schedules(status)
            if not schedules:
                return "No schedules found."
            return json.dumps(schedules, indent=2)
        except Exception as e:
            return f"Error listing schedules: {e}"


class CancelScheduleTool(BaseTool):
    name = "cancel_schedule"
    description = (
        "Cancel a scheduled mission by its schedule ID. The mission will not run again."
    )
    parameters = {
        "type": "object",
        "properties": {
            "schedule_id": {
                "type": "integer",
                "description": "The ID of the schedule to cancel"
            }
        },
        "required": ["schedule_id"]
    }
    category = "scheduling"

    async def execute(self, schedule_id: int) -> str:
        try:
            await ScheduleManager.cancel_schedule(schedule_id)
            return f"Schedule {schedule_id} cancelled."
        except Exception as e:
            return f"Error cancelling schedule: {e}"


class PauseScheduleTool(BaseTool):
    name = "pause_schedule"
    description = (
        "Pause a scheduled mission. It will not run until resumed."
    )
    parameters = {
        "type": "object",
        "properties": {
            "schedule_id": {
                "type": "integer",
                "description": "The ID of the schedule to pause"
            }
        },
        "required": ["schedule_id"]
    }
    category = "scheduling"

    async def execute(self, schedule_id: int) -> str:
        try:
            await ScheduleManager.pause_schedule(schedule_id)
            return f"Schedule {schedule_id} paused."
        except Exception as e:
            return f"Error pausing schedule: {e}"


class ResumeScheduleTool(BaseTool):
    name = "resume_schedule"
    description = (
        "Resume a paused scheduled mission. It will run again on its next scheduled time."
    )
    parameters = {
        "type": "object",
        "properties": {
            "schedule_id": {
                "type": "integer",
                "description": "The ID of the schedule to resume"
            }
        },
        "required": ["schedule_id"]
    }
    category = "scheduling"

    async def execute(self, schedule_id: int) -> str:
        try:
            await ScheduleManager.resume_schedule(schedule_id)
            return f"Schedule {schedule_id} resumed."
        except Exception as e:
            return f"Error resuming schedule: {e}"
