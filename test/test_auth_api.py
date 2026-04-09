from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import auth as auth_api
from core.config import settings
from services.jwt_service import generate_state_token


app = FastAPI()
app.include_router(auth_api.router)
client = TestClient(app)


def test_authorize_endpoint_redirects_to_google():
    response = client.get("/auth/oauth2/google/authorize", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith(settings.GOOGLE_AUTH_URI)


def test_authorize_endpoint_rejects_unlisted_redirect_override():
    response = client.get(
        "/auth/oauth2/google/authorize",
        params={"redirect_uri": "http://evil.example.com/login/success"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Redirect URI is not allowed."


def test_callback_redirects_to_frontend_with_one_time_code(monkeypatch):
    async def fake_exchange_google_authorization_code(_code: str):
        return {"access_token": "google-access-token"}

    async def fake_fetch_google_userinfo(_google_access_token: str):
        return {
            "id": "123",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.png",
        }

    stored = {}

    class FakeUser:
        id = 1
        email = "user@example.com"
        full_name = "Test User"
        avatar_url = "https://example.com/avatar.png"
        total_score = 0
        disabled = False

    def fake_get_or_create_google_user(_db, user_info):
        assert user_info["email"] == "user@example.com"
        return FakeUser()

    async def fake_store_refresh_token_jti(user_id: str, jti: str, ttl_seconds=None):
        stored["refresh_user_id"] = user_id
        stored["refresh_jti"] = jti
        stored["refresh_ttl_seconds"] = ttl_seconds

    async def fake_set_auth_code(user_id: str, payload: dict[str, str]) -> str:
        assert user_id == "1"
        assert "access_token" in payload
        assert "refresh_token" in payload
        return "one-time-auth-code"

    async def fake_set_user_cache(user_payload: dict[str, object]) -> None:
        stored["cached_user"] = user_payload

    monkeypatch.setattr(
        auth_api,
        "_exchange_google_authorization_code",
        fake_exchange_google_authorization_code,
    )
    monkeypatch.setattr(
        auth_api,
        "_fetch_google_userinfo",
        fake_fetch_google_userinfo,
    )
    monkeypatch.setattr(
        auth_api,
        "store_refresh_token_jti",
        fake_store_refresh_token_jti,
    )
    monkeypatch.setattr(auth_api, "get_or_create_google_user", fake_get_or_create_google_user)
    monkeypatch.setattr(auth_api, "set_user_cache", fake_set_user_cache)
    monkeypatch.setattr(auth_api, "set_auth_code", fake_set_auth_code)

    state = generate_state_token("google", "http://localhost:3000/login/success")
    response = client.get(
        "/auth/oauth2/google/callback",
        params={"code": "google-auth-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "http://localhost:3000/login/success?code=one-time-auth-code"
    )
    assert stored["refresh_user_id"] == "1"
    assert stored["refresh_jti"]
    assert stored["cached_user"]["id"] == 1
    assert stored["cached_user"]["email"] == "user@example.com"


def test_exchange_endpoint_returns_access_token_and_sets_cookie(monkeypatch):
    async def fake_consume_auth_code_atomic(code: str):
        assert code == "one-time-auth-code"
        return {
            "user_id": "google:123",
            "access_token": "local-access-token",
            "refresh_token": "local-refresh-token",
        }

    monkeypatch.setattr(
        auth_api,
        "consume_auth_code_atomic",
        fake_consume_auth_code_atomic,
    )

    response = client.post(
        "/auth/oauth2/exchange",
        json={"code": "one-time-auth-code"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "local-access-token"
    assert settings.AUTH_REFRESH_COOKIE_NAME in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_exchange_endpoint_rejects_invalid_or_expired_code(monkeypatch):
    async def fake_consume_auth_code_atomic(_code: str):
        return None

    monkeypatch.setattr(
        auth_api,
        "consume_auth_code_atomic",
        fake_consume_auth_code_atomic,
    )

    response = client.post(
        "/auth/oauth2/exchange",
        json={"code": "expired-code"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired one-time code."


def test_refresh_endpoint_rotates_refresh_token(monkeypatch):
    async def fake_get_refresh_token_owner(jti: str):
        assert jti == "old-jti"
        return "google:123"

    async def fake_store_refresh_token_jti(user_id: str, jti: str, ttl_seconds=None):
        assert user_id == "google:123"
        assert jti == "new-jti"

    async def fake_revoke_refresh_token_jti(jti: str):
        assert jti == "old-jti"

    def fake_verify_refresh_token(token: str):
        if token == "old-refresh-token":
            return {
                "sub": "google:123",
                "email": "user@example.com",
                "provider": "google",
                "name": "Test User",
                "picture": "https://example.com/avatar.png",
                "jti": "old-jti",
                "type": "refresh",
            }
        return {
            "sub": "google:123",
            "email": "user@example.com",
            "provider": "google",
            "name": "Test User",
            "picture": "https://example.com/avatar.png",
            "jti": "new-jti",
            "type": "refresh",
        }

    monkeypatch.setattr(auth_api, "get_refresh_token_owner", fake_get_refresh_token_owner)
    monkeypatch.setattr(auth_api, "store_refresh_token_jti", fake_store_refresh_token_jti)
    monkeypatch.setattr(auth_api, "revoke_refresh_token_jti", fake_revoke_refresh_token_jti)
    monkeypatch.setattr(auth_api, "verify_refresh_token", fake_verify_refresh_token)
    monkeypatch.setattr(auth_api, "create_access_token", lambda payload: "new-access-token")
    monkeypatch.setattr(auth_api, "create_refresh_token", lambda payload: "new-refresh-token")

    client.cookies.set(settings.AUTH_REFRESH_COOKIE_NAME, "old-refresh-token")
    response = client.post("/auth/refresh")
    client.cookies.clear()

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access-token"
    assert "new-refresh-token" in response.headers["set-cookie"]


def test_refresh_endpoint_rejects_missing_cookie():
    isolated_client = TestClient(app)
    response = isolated_client.post("/auth/refresh")
    isolated_client.close()

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token cookie is missing."
