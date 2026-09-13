from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Mission DTOs ───────────────────────────────────────────────────────────

class MissionDTO(BaseModel):
    id: int
    goal: str
    status: str
    uploaded_files: Optional[str] = None
    workflow_json: Optional[str] = None
    conversation_history: str = "[]"
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class MissionSummaryDTO(BaseModel):
    id: int
    goal: str
    status: str
    task_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    created_at: Optional[str] = None

class MissionCreateRequest(BaseModel):
    goal: str
    uploaded_files_json: Optional[str] = None

class MissionCreateResponse(BaseModel):
    mission_id: int
    message: str = "Mission queued for execution."

class MissionTimelineEntry(BaseModel):
    event_type: str
    timestamp: str
    detail: Optional[str] = None


# ─── Task DTOs ──────────────────────────────────────────────────────────────

class TaskDTO(BaseModel):
    id: int
    mission_id: int
    description: str
    assigned_agent: str
    status: str
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    execution_ms: int = 0
    retry_count: int = 0
    verification_status: Optional[str] = None
    verification_details: Optional[str] = None
    created_at: Optional[str] = None


# ─── DAG DTOs ───────────────────────────────────────────────────────────────

class DAGNode(BaseModel):
    id: str
    title: str
    status: str
    agent_role: str = ""
    x: float = 0
    y: float = 0

class DAGEdge(BaseModel):
    from_node: str
    to_node: str

class DAGLayout(BaseModel):
    nodes: List[DAGNode]
    edges: List[DAGEdge]


# ─── HITL DTOs ──────────────────────────────────────────────────────────────

class HITLInterruptDTO(BaseModel):
    id: int
    mission_id: int
    task_idx: Optional[int] = None
    context: Optional[str] = None
    error_message: Optional[str] = None
    status: str = "PENDING"
    created_at: Optional[str] = None

class HITLResolveRequest(BaseModel):
    guidance: str = "APPROVED"


# ─── Agent Persona DTOs ─────────────────────────────────────────────────────

class AgentPersonaDTO(BaseModel):
    id: Optional[int] = None
    role: str
    goal: str
    backstory: str
    tools: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None

class AgentPersonaCreateRequest(BaseModel):
    role: str
    goal: str
    backstory: str
    tools: List[str] = Field(default_factory=list)


# ─── Store DTOs ─────────────────────────────────────────────────────────────

class StorePackageDTO(BaseModel):
    id: str
    name: str
    version: str
    author: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    install_count: int = 0
    rating: float = 0.0
    installed: bool = False

class InstalledPackageDTO(BaseModel):
    id: int
    package_id: str
    version: str
    install_path: str
    status: str
    installed_at: Optional[str] = None


# ─── System DTOs ────────────────────────────────────────────────────────────

class SystemHealthDTO(BaseModel):
    status: str = "online"
    framework: str = "SquadOS"
    worker_active: bool = False
    uptime_seconds: float = 0.0
    active_missions: int = 0
    agents_online: int = 0

class SystemMetricsDTO(BaseModel):
    missions_total: int = 0
    missions_completed: int = 0
    missions_failed: int = 0
    tasks_total: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    agents_online: int = 0

class WorkerLogDTO(BaseModel):
    line: str
    timestamp: Optional[str] = None


# ─── Auth DTOs ──────────────────────────────────────────────────────────────

class AuthTokenRequest(BaseModel):
    api_key: str

class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    access_token: str
    expires_in: int = 3600


# ─── Generic ────────────────────────────────────────────────────────────────




# ─── WebSocket Event Frame ──────────────────────────────────────────────────

class WSEventFrame(BaseModel):
    version: int = 1
    sequence: int = 0
    type: str
    mission_id: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    payload: Dict[str, Any] = Field(default_factory=dict)
