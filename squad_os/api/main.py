from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from squad_os.orchestrator.manager import Manager
from squad_os.database.session import (
    get_all_personas, save_persona, delete_persona,
    get_next_queued_mission, update_mission, create_mission,
    add_to_queue
)
# Note: You'll need to import your tool inventory here
from squad_os.tools.registry import (
    WebSearchTool, FileWriterTool, ReadFileTool, TerminalTool,
    PythonRunnerTool, DashboardApprovalTool, MemorySearchTool,
    SetSharedValueTool, GetSharedValueTool, DelegateTaskTool,
    CommitProjectTool
)

app = FastAPI(title="SquadOS Production API", version="2.0.0")

class MissionRequest(BaseModel):
    goal: str
    uploaded_files_json: Optional[str] = None

class PersonaRequest(BaseModel):
    role: str
    goal: str
    backstory: str
    tools: List[str]

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

# Add more endpoints as needed for production monitoring
