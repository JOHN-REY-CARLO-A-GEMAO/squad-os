from __future__ import annotations

import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Simple self-contained JWT-like token auth
# No external dependency — uses HMAC-SHA256 with a server secret

SECRET_KEY: Optional[str] = None
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
REFRESH_EXPIRY_SECONDS = 2592000  # 30 days
_used_nonces: Set[str] = set()


def _get_secret() -> str:
    global SECRET_KEY
    if SECRET_KEY is None:
        SECRET_KEY = os.environ.get("SQUAD_OS_API_SECRET")
        if not SECRET_KEY:
            SECRET_KEY = hashlib.sha256(secrets.token_bytes(64)).hexdigest()
            os.environ["SQUAD_OS_API_SECRET"] = SECRET_KEY
    return SECRET_KEY


def _hmac(data: str) -> str:
    return hashlib.sha256(f"{data}:{_get_secret()}".encode()).hexdigest()


def _validate_api_key(api_key: str) -> bool:
    # Fail closed: the API key MUST be explicitly configured. Never fall back
    # to a known default — a hardcoded default key is a credential backdoor.
    expected = os.environ.get("SQUAD_OS_API_KEY", "")
    if not expected:
        return False
    return secrets.compare_digest(api_key, expected)


def create_tokens(device_name: str = "default") -> Dict[str, Any]:
    issued = int(time.time())
    exp = issued + TOKEN_EXPIRY_SECONDS
    refresh_exp = issued + REFRESH_EXPIRY_SECONDS

    nonce = secrets.token_hex(16)
    access_payload = f"access:{device_name}:{issued}:{exp}:{nonce}"
    refresh_payload = f"refresh:{device_name}:{issued}:{refresh_exp}:{nonce}"

    return {
        "access_token": f"{access_payload}.{_hmac(access_payload)}",
        "refresh_token": f"{refresh_payload}.{_hmac(refresh_payload)}",
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS,
    }


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = refresh_token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        if _hmac(payload) != sig:
            return None
        fields = payload.split(":")
        if len(fields) < 5 or fields[0] != "refresh":
            return None
        _, device_name, issued_s, exp_s, nonce = fields[:5]
        exp = int(exp_s)
        if time.time() > exp:
            return None
        issued = int(time.time())
        new_exp = issued + TOKEN_EXPIRY_SECONDS
        new_nonce = secrets.token_hex(16)
        new_payload = f"access:{device_name}:{issued}:{new_exp}:{new_nonce}"
        return {
            "access_token": f"{new_payload}.{_hmac(new_payload)}",
            "expires_in": TOKEN_EXPIRY_SECONDS,
        }
    except Exception:
        return None


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        if _hmac(payload) != sig:
            return None
        fields = payload.split(":")
        if len(fields) < 5 or fields[0] != "access":
            return None
        _, device_name, issued_s, exp_s, nonce = fields[:5]
        if time.time() > int(exp_s):
            return None
        return {"device": device_name, "issued": int(issued_s), "exp": int(exp_s)}
    except Exception:
        return None


security = HTTPBearer(auto_error=False)


def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        return None
    return verify_token(credentials.credentials)
