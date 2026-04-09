from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from schemas.auth import AuthAccessTokenResponse, OAuthCodeExchangeRequest
from services.jwt_service import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_state_token,
)
from services.oauth_authorize_service import (
    append_query_params,
    build_google_authorization_url,
    resolve_frontend_redirect_uri,
)
from services.redis_service import (
    consume_auth_code_atomic,
    get_refresh_token_owner,
    revoke_refresh_token_jti,
    set_auth_code,
    set_user_cache,
    store_refresh_token_jti,
)
from services.user import get_or_create_google_user, serialize_user


router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def _exchange_google_authorization_code(code: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=GOOGLE_HTTP_TIMEOUT) as client:
            response = await client.post(
                settings.GOOGLE_TOKEN_URI,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Google token endpoint.",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange failed.",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google token endpoint returned an invalid response.",
        ) from exc

    if not payload.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange did not return an access token.",
        )
    return payload


async def _fetch_google_userinfo(google_access_token: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=GOOGLE_HTTP_TIMEOUT) as client:
            response = await client.get(
                settings.GOOGLE_USERINFO_URI,
                headers={
                    "Authorization": f"Bearer {google_access_token}",
                    "Accept": "application/json",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Google userinfo endpoint.",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch Google user info.",
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google userinfo endpoint returned an invalid response.",
        ) from exc


def _set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.JWT_REFRESH_TTL_SECONDS,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=settings.AUTH_COOKIE_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _token_response(access_token: str) -> AuthAccessTokenResponse:
    return AuthAccessTokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_TTL_SECONDS,
    )


@router.get("/oauth2/google/authorize")
async def authorize_google_oauth2(
    redirect_uri: str | None = Query(
        default=None,
        description="Optional allowed frontend redirect URI.",
    ),
):
    authorization_url = build_google_authorization_url(
        override_redirect=redirect_uri,
    )
    return RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.get("/oauth2/google/callback")
async def callback_google_oauth2(
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    state_payload = verify_state_token(state)
    if state_payload.get("provider") != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state provider mismatch.",
        )

    frontend_redirect_uri = resolve_frontend_redirect_uri(
        state_payload.get("redirect_uri"),
    )

    google_token_payload = await _exchange_google_authorization_code(code)
    google_user_info = await _fetch_google_userinfo(
        google_token_payload["access_token"],
    )
    user = get_or_create_google_user(db, google_user_info)
    serialized_user = serialize_user(user)
    await set_user_cache(serialized_user)

    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "picture": user.avatar_url,
        "provider": "google",
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)
    refresh_claims = verify_refresh_token(refresh_token)

    await store_refresh_token_jti(
        user_id=str(user.id),
        jti=refresh_claims["jti"],
    )
    one_time_code = await set_auth_code(
        user_id=str(user.id),
        payload={
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )

    redirect_target = append_query_params(frontend_redirect_uri, {"code": one_time_code})
    return RedirectResponse(
        url=redirect_target,
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post(
    "/oauth2/exchange",
    response_model=AuthAccessTokenResponse,
)
async def exchange_token(
    payload: OAuthCodeExchangeRequest,
    response: Response,
):
    auth_payload = await consume_auth_code_atomic(payload.code)
    if not auth_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired one-time code.",
        )

    access_token = auth_payload.get("access_token")
    refresh_token = auth_payload.get("refresh_token")
    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored authentication payload is incomplete.",
        )

    _set_refresh_token_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post(
    "/refresh",
    response_model=AuthAccessTokenResponse,
)
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=settings.AUTH_REFRESH_COOKIE_NAME,
    ),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie is missing.",
        )

    refresh_claims = verify_refresh_token(refresh_token)
    token_owner = await get_refresh_token_owner(refresh_claims["jti"])
    if token_owner != refresh_claims["sub"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is revoked or no longer active.",
        )

    token_payload = {
        "sub": refresh_claims["sub"],
        "email": refresh_claims.get("email"),
        "name": refresh_claims.get("name"),
        "picture": refresh_claims.get("picture"),
        "provider": refresh_claims.get("provider"),
    }
    new_access_token = create_access_token(token_payload)
    new_refresh_token = create_refresh_token(token_payload)
    new_refresh_claims = verify_refresh_token(new_refresh_token)

    await store_refresh_token_jti(
        user_id=refresh_claims["sub"],
        jti=new_refresh_claims["jti"],
    )
    await revoke_refresh_token_jti(refresh_claims["jti"])

    _set_refresh_token_cookie(response, new_refresh_token)
    return _token_response(new_access_token)
