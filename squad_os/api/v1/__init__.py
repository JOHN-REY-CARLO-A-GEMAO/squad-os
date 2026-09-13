from fastapi import APIRouter, Depends

from squad_os.api.auth import require_auth

# Every /api/v1 route requires a valid access token by default.
v1_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])

# Public /api/v1 routes that must be reachable WITHOUT a token (the login
# flow and liveness probes). Endpoints go here explicitly — FastAPI merges
# router-level dependencies, so per-route `dependencies=[]` does NOT opt out.
public_router = APIRouter(prefix="/api/v1")

from squad_os.api.v1 import hitl, missions, store, system

v1_router.include_router(missions.router)
v1_router.include_router(store.router)
v1_router.include_router(hitl.router)
v1_router.include_router(system.router)
public_router.include_router(system.public_router)
