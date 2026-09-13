from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Event Types ────────────────────────────────────────────────────────────

class EventType(str, Enum):
    MISSION_CREATED = "mission.created"
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    MISSION_PAUSED = "mission.paused"
    MISSION_RESUMED = "mission.resumed"
    MISSION_CANCELLED = "mission.cancelled"

    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_SKIPPED = "task.skipped"
    TASK_PAUSED = "task.paused"

    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"

    INTERRUPT_CREATED = "interrupt.created"
    INTERRUPT_RESOLVED = "interrupt.resolved"

    WORKER_HEARTBEAT = "worker.heartbeat"
    WORKER_STARTED = "worker.started"
    WORKER_STOPPED = "worker.stopped"

    AGENT_SPAWNED = "agent.spawned"
    AGENT_THINKING = "agent.thinking"
    AGENT_DONE = "agent.done"

    SYSTEM_METRICS = "system.metrics"
    SYSTEM_ERROR = "system.error"

    STORE_PACKAGE_INSTALLED = "store.package_installed"
    STORE_PACKAGE_REMOVED = "store.package_removed"

    PLAN_STARTED = "plan.started"
    PLAN_FINISHED = "plan.finished"

    GATE_PASSED = "gate.passed"
    GATE_FAILED = "gate.failed"

    SCHEDULE_TRIGGERED = "schedule.triggered"

# ─── Event Payloads ─────────────────────────────────────────────────────────

class BaseEvent(BaseModel):
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mission_id: Optional[int] = None

class MissionEvent(BaseEvent):
    goal: Optional[str] = None
    status: Optional[str] = None

class TaskEvent(BaseEvent):
    task_id: Optional[int] = None
    task_idx: Optional[int] = None
    description: Optional[str] = None
    agent_role: Optional[str] = None
    status: Optional[str] = None

class ApprovalEvent(BaseEvent):
    approval_id: Optional[int] = None
    task_id: Optional[int] = None
    message: Optional[str] = None
    resolved_status: Optional[str] = None

class InterruptEvent(BaseEvent):
    interrupt_id: Optional[int] = None
    task_idx: Optional[int] = None
    context: Optional[str] = None
    resolved_guidance: Optional[str] = None

class HeartbeatEvent(BaseEvent):
    active_missions: int = 0
    agents_active: int = 0

class AgentEvent(BaseEvent):
    agent_role: Optional[str] = None
    action: Optional[str] = None
    detail: Optional[str] = None

class MetricEvent(BaseEvent):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    agents_online: int = 0

class StoreEvent(BaseEvent):
    package_id: Optional[str] = None
    package_name: Optional[str] = None
    version: Optional[str] = None

class GateEvent(BaseEvent):
    task_idx: Optional[int] = None
    gate_name: Optional[str] = None
    status: Optional[str] = None
    details: Optional[str] = None

class PlanEvent(BaseEvent):
    task_count: int = 0
    suggested_parallelism: int = 1

class ScheduleEvent(BaseEvent):
    schedule_id: Optional[int] = None
    mission_goal: Optional[str] = None

# ─── Event Bus ──────────────────────────────────────────────────────────────

EventHandler = Callable[[BaseEvent], Awaitable[None]]

class EventBus:
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType, handler: EventHandler):
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: EventHandler):
        self._wildcard_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        hs = self._handlers.get(event_type, [])
        if handler in hs:
            hs.remove(handler)

    async def publish(self, event: BaseEvent):
        hs = list(self._handlers.get(event.event_type, []))
        whs = list(self._wildcard_handlers)
        for h in hs + whs:
            try:
                await h(event)
            except Exception as e:
                logger.error(f"Event handler failed for {event.event_type}: {e}")

    def clear(self):
        self._handlers.clear()
        self._wildcard_handlers.clear()

_bus: Optional[EventBus] = None

def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus

def reset_bus():
    global _bus
    if _bus:
        _bus.clear()
    _bus = None
