from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException

from core.config import settings
from services.jwt_service import generate_state_token, verify_refresh_token, verify_state_token
from services.oauth_authorize_service import (
    build_google_authorization_url,
    resolve_frontend_redirect_uri,
)


def test_state_token_round_trip_preserves_provider_and_redirect():
    token = generate_state_token(
        "google",
        "http://localhost:3000/login/success",
    )

    payload = verify_state_token(token)

    assert payload["provider"] == "google"
    assert payload["redirect_uri"] == "http://localhost:3000/login/success"
    assert payload["type"] == "state"


def test_refresh_token_contains_jti_and_subject():
    token = verify_refresh_token(
        __import__("services.jwt_service", fromlist=["create_refresh_token"]).create_refresh_token(
            {"sub": "google:123", "email": "user@example.com", "provider": "google"}
        )
    )

    assert token["sub"] == "google:123"
    assert token["type"] == "refresh"
    assert "jti" in token


def test_build_google_authorization_url_contains_expected_params():
    authorization_url = build_google_authorization_url()
    parsed = urlparse(authorization_url)
    query = parse_qs(parsed.query)

    assert query["client_id"] == [settings.GOOGLE_CLIENT_ID]
    assert query["redirect_uri"] == [settings.GOOGLE_REDIRECT_URI]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]

    state_payload = verify_state_token(query["state"][0])
    assert state_payload["provider"] == "google"
    assert state_payload["redirect_uri"] == settings.AUTH_FRONTEND_SUCCESS_REDIRECT_URI


def test_build_google_authorization_url_accepts_allowlisted_override_redirect():
    authorization_url = build_google_authorization_url(
        "http://localhost:5173/login/success",
    )
    parsed = urlparse(authorization_url)
    query = parse_qs(parsed.query)

    state_payload = verify_state_token(query["state"][0])
    assert state_payload["redirect_uri"] == "http://localhost:5173/login/success"


def test_resolve_frontend_redirect_uri_rejects_unlisted_redirect():
    with pytest.raises(HTTPException, match="Redirect URI is not allowed"):
        resolve_frontend_redirect_uri("http://evil.example.com/login/success")
