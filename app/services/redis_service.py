from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

from core.config import settings


redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _auth_code_key(code: str) -> str:
    return f"auth:code:{code}"


def _refresh_token_key(jti: str) -> str:
    return f"auth:refresh:{jti}"


def _user_cache_key(user_id: int | str) -> str:
    return f"auth:user:{user_id}"


async def set_auth_code(user_id: str, payload: dict[str, str]) -> str:
    code = str(uuid4())
    data = {
        "user_id": user_id,
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
    }
    await redis_client.set(
        _auth_code_key(code),
        json.dumps(data),
        ex=settings.AUTH_CODE_TTL_SECONDS,
    )
    return code


async def consume_auth_code_atomic(code: str) -> dict[str, Any] | None:
    raw = await redis_client.getdel(_auth_code_key(code))
    if not raw:
        return None
    return json.loads(raw)


async def store_refresh_token_jti(
    user_id: str,
    jti: str,
    ttl_seconds: int | None = None,
) -> None:
    await redis_client.set(
        _refresh_token_key(jti),
        user_id,
        ex=ttl_seconds or settings.JWT_REFRESH_TTL_SECONDS,
    )


async def get_refresh_token_owner(jti: str) -> str | None:
    owner = await redis_client.get(_refresh_token_key(jti))
    return owner if owner else None


async def revoke_refresh_token_jti(jti: str) -> None:
    await redis_client.delete(_refresh_token_key(jti))


async def set_user_cache(user_payload: dict[str, Any]) -> None:
    await redis_client.set(
        _user_cache_key(user_payload["id"]),
        json.dumps(user_payload),
        ex=settings.AUTH_USER_CACHE_TTL_SECONDS,
    )


async def get_user_cache(user_id: int | str) -> dict[str, Any] | None:
    raw = await redis_client.get(_user_cache_key(user_id))
    if not raw:
        return None
    return json.loads(raw)


async def delete_user_cache(user_id: int | str) -> None:
    await redis_client.delete(_user_cache_key(user_id))


async def close_redis_client() -> None:
    await redis_client.aclose()
