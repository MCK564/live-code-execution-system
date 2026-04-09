from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from fastapi import HTTPException, status

from core.config import settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _encode_token(payload: dict[str, Any], ttl_seconds: int, token_type: str) -> str:
    now = _utc_now()
    claims = payload.copy()
    claims.update(
        {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
            "iss": settings.AUTH_ISSUER,
            "type": token_type,
        }
    )
    return jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _decode_token(
    token: str,
    *,
    expected_type: str,
    exception_status_code: int,
    exception_detail: str,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.AUTH_ISSUER,
            options={"require": ["exp", "iat", "iss", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=exception_status_code,
            detail=exception_detail,
        ) from exc

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=exception_status_code,
            detail=exception_detail,
        )
    return payload


def create_access_token(payload: dict[str, Any]) -> str:
    return _encode_token(
        payload=payload,
        ttl_seconds=settings.JWT_TTL_SECONDS,
        token_type="access",
    )


def create_refresh_token(payload: dict[str, Any]) -> str:
    refresh_payload = payload.copy()
    refresh_payload["jti"] = str(uuid4())
    return _encode_token(
        payload=refresh_payload,
        ttl_seconds=settings.JWT_REFRESH_TTL_SECONDS,
        token_type="refresh",
    )


def generate_state_token(provider: str, redirect_uri: str) -> str:
    return _encode_token(
        payload={
            "provider": provider,
            "redirect_uri": redirect_uri,
        },
        ttl_seconds=settings.JWT_STATE_TTL_SECONDS,
        token_type="state",
    )


def verify_state_token(token: str) -> dict[str, Any]:
    return _decode_token(
        token,
        expected_type="state",
        exception_status_code=status.HTTP_400_BAD_REQUEST,
        exception_detail="Invalid or expired OAuth state.",
    )


def verify_access_token(token: str) -> dict[str, Any]:
    payload = _decode_token(
        token,
        expected_type="access",
        exception_status_code=status.HTTP_401_UNAUTHORIZED,
        exception_detail="Invalid or expired access token.",
    )
    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing required claims.",
        )
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    payload = _decode_token(
        token,
        expected_type="refresh",
        exception_status_code=status.HTTP_401_UNAUTHORIZED,
        exception_detail="Invalid or expired refresh token.",
    )
    if "jti" not in payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing required claims.",
        )
    return payload
