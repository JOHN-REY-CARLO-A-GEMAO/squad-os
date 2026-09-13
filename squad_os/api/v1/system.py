from __future__ import annotations

from fastapi import APIRouter

from squad_os.api.schemas import AuthTokenRequest, AuthTokenResponse, SystemHealthDTO, SystemMetricsDTO, TokenRefreshRequest, TokenRefreshResponse
from squad_os.api.auth import create_tokens, refresh_access_token, _validate_api_key
from squad_os.api.services.system_service import system_service

# Protected routes (inherit the v1_router auth dependency).
router = APIRouter(prefix="/system", tags=["System"])

# Public routes (login flow + liveness) — included separately in main.py.
public_router = APIRouter(prefix="/system", tags=["System"])


@public_router.get("/health", response_model=SystemHealthDTO)
async def health_check():
    # Public: liveness probe for monitoring. No sensitive data.
    return await system_service.get_health()


@router.get("/metrics", response_model=SystemMetricsDTO)
async def get_metrics():
    return await system_service.get_metrics()


@public_router.post("/auth/token", response_model=AuthTokenResponse)
async def exchange_token(req: AuthTokenRequest):
    # Public: this is the login endpoint (exchanges the API key for tokens).
    if not _validate_api_key(req.api_key):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid API key")
    return create_tokens()


@public_router.post("/auth/refresh", response_model=TokenRefreshResponse)
async def refresh_token(req: TokenRefreshRequest):
    # Public: refresh requires a valid (HMAC-signed, unexpired) refresh token itself.
    result = refresh_access_token(req.refresh_token)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return TokenRefreshResponse(**result)
