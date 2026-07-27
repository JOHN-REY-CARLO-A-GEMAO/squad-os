from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from squad_os.orchestrator.manager import Manager
from squad_os.database.session import (
    get_all_personas, save_persona, delete_persona,
    get_next_queued_mission, update_mission, create_mission,
    add_to_queue, get_workspaces, get_conversations, get_conversation_by_id,
    get_conversation_events, update_conversation_memory_fields,
    get_conversation_memory, search_conversation_events, register_device,
    get_active_devices, revoke_device, register_broadcast_callback
)
# Note: You'll need to import your tool inventory here
from squad_os.tools.registry import (
    WebSearchTool, FileWriterTool, ReadFileTool, TerminalTool,
    PythonRunnerTool, DashboardApprovalTool, MemorySearchTool,
    SetSharedValueTool, GetSharedValueTool, DelegateTaskTool,
    CommitProjectTool
)

app = FastAPI(title="SquadOS Production API with Mobile Remote Companion Support", version="2.0.0")

# --- CORE SCHEMAS ---

class MissionRequest(BaseModel):
    goal: str
    uploaded_files_json: Optional[str] = None

class PersonaRequest(BaseModel):
    role: str
    goal: str
    backstory: str
    tools: List[str]

# --- MOBILE REMOTE COMPANION SCHEMAS ---

class HandshakeRequest(BaseModel):
    client_version: str
    capabilities: List[str]

class HandshakeResponse(BaseModel):
    server_version: str
    schema_version: str
    negotiated_capabilities: Dict[str, bool]
    max_payload_mb: int

class UpdateContextRequest(BaseModel):
    context_memory: Dict[str, str]

class UpdateContextResponse(BaseModel):
    status: str
    updated_context_memory: Dict[str, str]

class PairRequest(BaseModel):
    pairing_url: str
    ticket_version: int
    nonce: str
    device_id: str

class PairResponse(BaseModel):
    status: str
    message: str

class TokenRequest(BaseModel):
    device_id: str
    nonce: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int

# --- WEBSOCKET CONNECTION MANAGER ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, conversation_id: int, websocket: WebSocket):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, conversation_id: int, websocket: WebSocket):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def broadcast(self, conversation_id: int, message: dict):
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

ws_manager = ConnectionManager()

# Hook the database broadcast triggers to our WebSocket manager
async def db_broadcast_hook(conversation_id: int, payload: dict):
    await ws_manager.broadcast(conversation_id, payload)

register_broadcast_callback(db_broadcast_hook)

# --- API ENDPOINTS ---

@app.get("/health")
async def health_check():
    return {"status": "online", "framework": "SquadOS"}

@app.get("/personas")
async def list_personas():
    return await get_all_personas()

@app.post("/personas")
async def create_new_persona(req: PersonaRequest):
    await save_persona(req.role, req.goal, req.backstory, req.tools)
    return {"message": f"Persona '{req.role}' saved."}

@app.delete("/personas/{role}")
async def remove_persona(role: str):
    await delete_persona(role)
    return {"message": f"Persona '{role}' deleted."}

@app.post("/missions/dispatch")
async def dispatch_mission(req: MissionRequest, background_tasks: BackgroundTasks):
    await add_to_queue(req.goal, req.uploaded_files_json)
    return {"message": "Mission queued for execution."}

# --- MOBILE REMOTE COMPANION REST API (v1.0 Architecture) ---

@app.post("/api/v1/handshake", response_model=HandshakeResponse)
async def handshake(req: HandshakeRequest):
    negotiated = {cap: True for cap in req.capabilities}
    # Ensure standard required capabilities are flagged
    negotiated["nested_events"] = True
    negotiated["mission_snapshots"] = True
    negotiated["qr_pairing"] = True

    return HandshakeResponse(
        server_version="2.0.4",
        schema_version="1.2.0",
        negotiated_capabilities=negotiated,
        max_payload_mb=15
    )

@app.get("/api/v1/workspaces")
async def list_workspaces():
    workspaces = await get_workspaces()
    return {"workspaces": workspaces}

@app.get("/api/v1/workspaces/{workspace_id}/conversations")
async def list_workspace_conversations(workspace_id: int):
    conversations = await get_conversations(workspace_id)
    return {"conversations": conversations}

@app.get("/api/v1/conversations/{id}")
async def fetch_unified_timeline(
    id: int,
    limit: int = Query(50, ge=1, le=100),
    parent_only: bool = False,
    since_sequence_id: Optional[int] = None
):
    conv = await get_conversation_by_id(id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation {id} not found.")

    events = await get_conversation_events(
        conversation_id=id,
        limit=limit,
        parent_only=parent_only,
        since_sequence_id=since_sequence_id
    )

    # Parse event payloads back to JSON dicts
    parsed_events = []
    for ev in events:
        try:
            payload = json.loads(ev["payload_json"])
        except Exception:
            payload = {"raw": ev["payload_json"]}

        parsed_events.append({
            "id": ev["id"],
            "parent_event_id": ev["parent_event_id"],
            "sequence_id": ev["sequence_id"],
            "event_namespace": ev["event_namespace"],
            "event_type": ev["event_type"],
            "payload_schema_version": ev["payload_schema_version"],
            "created_at": ev["created_at"],
            "mission_id": ev["mission_id"],
            "payload": payload
        })

    return {
        "conversation_id": conv["id"],
        "workspace_id": conv["workspace_id"],
        "title": conv["title"],
        "summary": conv["summary"],
        "goal": conv["goal"],
        "active_model": conv["active_model"],
        "temperature": conv["temperature"],
        "system_prompt": conv["system_prompt"],
        "events": parsed_events
    }

@app.put("/api/v1/conversations/{id}/context", response_model=UpdateContextResponse)
async def update_conversation_context(id: int, req: UpdateContextRequest):
    conv = await get_conversation_by_id(id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation {id} not found.")

    await update_conversation_memory_fields(id, req.context_memory)
    updated = await get_conversation_memory(id)
    return UpdateContextResponse(
        status="SUCCESS",
        updated_context_memory=updated
    )

@app.get("/api/v1/conversations/{id}/search")
async def search_conversation(id: int, q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    conv = await get_conversation_by_id(id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation {id} not found.")

    results = await search_conversation_events(id, q, limit)
    parsed_results = []
    for r in results:
        try:
            payload = json.loads(r["payload_json"])
        except Exception:
            payload = {}

        snippet = payload.get("message", payload.get("thought", payload.get("output", r["payload_json"])))
        parsed_results.append({
            "event_id": r["id"],
            "event_namespace": r["event_namespace"],
            "event_type": r["event_type"],
            "similarity_score": 1.0,  # FTS match
            "matched_snippet": snippet[:200] if snippet else "",
            "timestamp": r["created_at"]
        })

    return {
        "query": q,
        "engine_used": "sqlite_fts",
        "results": parsed_results
    }

# --- SECURE QR PAIRING & TOKEN ENDPOINTS ---

@app.post("/api/v1/pair/request", response_model=PairResponse)
async def pairing_request(req: PairRequest):
    # Register device to devices table
    device_id = await register_device(
        push_token=f"token_{req.device_id}",
        platform="ios" if "iphone" in req.device_id.lower() else "android",
        device_model="SquadCompanionDevice",
        user_id="default_user"
    )
    return PairResponse(
        status="SUCCESS",
        message=f"Device pairing request registered with system ID {device_id}."
    )

@app.get("/api/v1/pair/token", response_model=TokenResponse)
async def pairing_token(device_id: str = Query(...), nonce: str = Query(...)):
    # Generates asymmetrical JWT mock token pair
    return TokenResponse(
        access_token=f"mock_access_jwt_token_for_{device_id}",
        refresh_token=f"mock_refresh_jwt_token_for_{device_id}",
        expires_in=900
    )

# --- WEBSOCKET EVENT STREAM (v1.0 Architecture) ---

@app.websocket("/api/v1/streams")
async def websocket_endpoint(websocket: WebSocket, conversation_id: int = 1):
    await ws_manager.connect(conversation_id, websocket)
    try:
        while True:
            # Keep-alive loop & receiving messages/commands from client
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Implement client command execution (Section 4.2.3: Idempotency support)
                if "request_id" in msg and "action" in msg:
                    # Echo command ack with the unique client request_id
                    await websocket.send_json({
                        "type": "COMMAND_ACK",
                        "request_id": msg["request_id"],
                        "status": "PROCESSED",
                        "action": msg["action"]
                    })
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(conversation_id, websocket)
