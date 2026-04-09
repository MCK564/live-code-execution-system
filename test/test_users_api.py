from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import users as users_api
from services.jwt_service import create_access_token


app = FastAPI()
app.include_router(users_api.router)
client = TestClient(app)


def _access_token(subject: str = "1") -> str:
    return create_access_token(
        {
            "sub": subject,
            "email": "user@example.com",
            "name": "Test User",
            "provider": "google",
        }
    )


def test_get_current_user_returns_cached_user(monkeypatch):
    async def fake_get_user_cache(user_id: int):
        assert user_id == 1
        return {
            "id": 1,
            "email": "user@example.com",
            "full_name": "Cached User",
            "avatar_url": "https://example.com/cached.png",
            "total_score": 12,
            "disabled": False,
        }

    def fail_get_user_by_id(*_args, **_kwargs):
        raise AssertionError("DB lookup should not run on cache hit")

    monkeypatch.setattr(users_api, "get_user_cache", fake_get_user_cache)
    monkeypatch.setattr(users_api, "get_user_by_id", fail_get_user_by_id)

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {_access_token()}"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Cached User"


def test_get_current_user_falls_back_to_db_and_rehydrates_cache(monkeypatch):
    stored = {}

    async def fake_get_user_cache(user_id: int):
        assert user_id == 1
        return None

    class FakeUser:
        id = 1
        email = "user@example.com"
        full_name = "DB User"
        avatar_url = "https://example.com/db.png"
        total_score = 42
        disabled = False

    def fake_get_user_by_id(_db, user_id: int):
        assert user_id == 1
        return FakeUser()

    async def fake_set_user_cache(user_payload: dict[str, object]) -> None:
        stored["user_payload"] = user_payload

    monkeypatch.setattr(users_api, "get_user_cache", fake_get_user_cache)
    monkeypatch.setattr(users_api, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(users_api, "set_user_cache", fake_set_user_cache)

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {_access_token()}"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "DB User"
    assert stored["user_payload"]["id"] == 1
    assert stored["user_payload"]["total_score"] == 42


def test_get_current_user_requires_bearer_header():
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header is missing."
