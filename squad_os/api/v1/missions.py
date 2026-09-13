from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from squad_os.api.schemas import (
    DAGLayout, MissionCreateRequest, MissionCreateResponse,
    MissionDTO, MissionSummaryDTO, MissionTimelineEntry, TaskDTO,
)
from squad_os.api.services.mission_service import mission_service

router = APIRouter(prefix="/missions", tags=["Missions"])


@router.get("", response_model=list[MissionSummaryDTO])
async def list_missions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await mission_service.list_missions(status=status, limit=limit, offset=offset)


@router.post("", response_model=MissionCreateResponse, status_code=201)
async def create_mission(req: MissionCreateRequest):
    mission_id = await mission_service.queue_mission(req.goal, req.uploaded_files_json)
    return MissionCreateResponse(mission_id=mission_id)


@router.get("/{mission_id}", response_model=MissionDTO)
async def get_mission(mission_id: int):
    mission = await mission_service.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.get("/{mission_id}/tasks", response_model=list[TaskDTO])
async def get_mission_tasks(mission_id: int):
    return await mission_service.get_mission_tasks(mission_id)


@router.get("/{mission_id}/timeline", response_model=list[MissionTimelineEntry])
async def get_mission_timeline(mission_id: int):
    return await mission_service.get_mission_timeline(mission_id)


@router.get("/{mission_id}/dag", response_model=DAGLayout)
async def get_mission_dag(mission_id: int):
    dag = await mission_service.get_mission_dag(mission_id)
    if not dag:
        raise HTTPException(status_code=404, detail="DAG not available for this mission")
    return dag


@router.post("/{mission_id}/pause")
async def pause_mission(mission_id: int):
    ok = await mission_service.pause_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"message": "Mission paused"}


@router.post("/{mission_id}/resume")
async def resume_mission(mission_id: int):
    ok = await mission_service.resume_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"message": "Mission resumed"}


@router.post("/{mission_id}/cancel")
async def cancel_mission(mission_id: int):
    ok = await mission_service.cancel_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"message": "Mission cancelled"}
