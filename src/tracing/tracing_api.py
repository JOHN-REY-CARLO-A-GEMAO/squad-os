from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="squad-os Graph API")

class TraceInput(BaseModel):
    tracing_context: Dict[str, Any]

@app.post("/api/v1/runs/{run_id}/graph")
async def generate_graph(run_id: str, input: TraceInput):
    """
    Generate a Mermaid graph representation from a trace context for the specified run.
    
    Parameters:
        run_id (str): Identifier of the run for which the graph is generated.
        input (TraceInput): Request body containing `tracing_context` used to build the graph.
    
    Returns:
        dict: A JSON-serializable mapping with keys:
            - "run_id": the provided `run_id`
            - "mermaid_graph": the generated Mermaid-format graph as a string
    
    Raises:
        HTTPException: With status_code 500 if graph generation fails; `detail` contains the underlying exception message.
    """
    try:
        from .tracing_parser import TraceParser
        parser = TraceParser(input.tracing_context)
        return {"run_id": run_id, "mermaid_graph": parser.to_mermaid()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))