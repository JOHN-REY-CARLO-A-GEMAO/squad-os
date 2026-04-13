from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="squad-os Graph API")

class TraceInput(BaseModel):
    tracing_context: Dict[str, Any]

@app.post("/api/v1/runs/{run_id}/graph")
async def generate_graph(run_id: str, input: TraceInput):
    try:
        from .tracing_parser import TraceParser
        parser = TraceParser(input.tracing_context)
        return {"run_id": run_id, "mermaid_graph": parser.to_mermaid()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))