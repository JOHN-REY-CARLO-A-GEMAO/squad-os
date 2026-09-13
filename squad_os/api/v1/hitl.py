from __future__ import annotations

from fastapi import APIRouter, HTTPException

from squad_os.api.schemas import HITLInterruptDTO, HITLResolveRequest
from squad_os.api.services.hitl_service import hitl_service

router = APIRouter(prefix="/hitl", tags=["HITL"])


@router.get("/pending", response_model=list[HITLInterruptDTO])
async def get_pending_interrupts():
    return await hitl_service.get_pending_interrupts()


@router.get("/pending/count")
async def get_pending_count():
    count = await hitl_service.get_pending_count()
    return {"count": count}


@router.get("/missions/{mission_id}", response_model=list[HITLInterruptDTO])
async def get_mission_interrupts(mission_id: int):
    return await hitl_service.get_mission_interrupts(mission_id)


@router.post("/{interrupt_id}/approve")
async def approve_interrupt(interrupt_id: int):
    ok = await hitl_service.resolve_interrupt(interrupt_id, "APPROVED")
    if not ok:
        raise HTTPException(status_code=404, detail="Interrupt not found")
    return {"message": "Interrupt approved"}


@router.post("/{interrupt_id}/reject")
async def reject_interrupt(interrupt_id: int, req: HITLResolveRequest):
    ok = await hitl_service.resolve_interrupt(interrupt_id, req.guidance)
    if not ok:
        raise HTTPException(status_code=404, detail="Interrupt not found")
    return {"message": "Interrupt rejected"}
