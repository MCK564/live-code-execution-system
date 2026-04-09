from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import HTTPException, status

from core.config import settings
from services.jwt_service import generate_state_token


def _validate_redirect_uri(redirect_uri: str) -> str:
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI must be an absolute http(s) URL.",
        )

    if redirect_uri not in settings.auth_redirect_allowlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI is not allowed.",
        )

    return redirect_uri


def resolve_frontend_redirect_uri(override_redirect: str | None = None) -> str:
    redirect_uri = override_redirect or settings.AUTH_FRONTEND_SUCCESS_REDIRECT_URI
    return _validate_redirect_uri(redirect_uri)


def build_google_authorization_url(override_redirect: str | None = None) -> str:
    frontend_redirect_uri = resolve_frontend_redirect_uri(override_redirect)
    state = generate_state_token("google", frontend_redirect_uri)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{settings.GOOGLE_AUTH_URI}?{urlencode(params)}"


def append_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_params.update(params)
    return urlunparse(parsed._replace(query=urlencode(query_params)))


def build_google_authorize_url(override_redirect: str | None = None) -> str:
    return build_google_authorization_url(override_redirect=override_redirect)
