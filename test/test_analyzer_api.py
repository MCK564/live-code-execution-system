from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.analyzer import router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_http_analyzer_returns_python_alerts():
    response = client.post(
        "/analyzer",
        json={
            "language": "python",
            "source_code": "while True:\n    value = 10 / 0\n",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "python"
    assert body["result"]["parse_error"] is None
    assert any(alert["kind"] == "infinite_loop" for alert in body["result"]["alerts"])


def test_http_analyzer_accepts_code_alias():
    response = client.post(
        "/analyzer",
        json={
            "language": "python",
            "code": "while True:\n    value = 10 / 0\n",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any(alert["kind"] == "infinite_loop" for alert in body["result"]["alerts"])


def test_http_analyzer_rejects_missing_source_code():
    response = client.post(
        "/analyzer",
        json={"language": "python"},
    )

    assert response.status_code == 422


def test_websocket_analyzer_returns_result_and_pong():
    with client.websocket_connect("/analyzer/ws/session-123") as websocket:
        websocket.send_json({"type": "ping", "ts": 123})
        pong = websocket.receive_json()
        assert pong == {"type": "pong", "ts": 123}

        websocket.send_json(
            {
                "type": "analyze.request",
                "request_id": "req-1",
                "version": 5,
                "language": "java",
                "source_code": "public class Main { void f(){ while(true){ int x = 1; } } }",
            }
        )
        result = websocket.receive_json()

    assert result["type"] == "analyze.result"
    assert result["session_id"] == "session-123"
    assert result["request_id"] == "req-1"
    assert result["version"] == 5
    assert result["language"] == "java"
    assert any(alert["kind"] == "infinite_loop" for alert in result["result"]["alerts"])


def test_websocket_analyzer_accepts_code_alias():
    with client.websocket_connect("/analyzer/ws/session-456") as websocket:
        websocket.send_json(
            {
                "type": "analyze.request",
                "request_id": "req-2",
                "version": 2,
                "language": "cpp",
                "code": "int main(){ int x = 10 / 0; return x; }",
            }
        )
        result = websocket.receive_json()

    assert result["type"] == "analyze.result"
    assert any(alert["kind"] == "math_risk" for alert in result["result"]["alerts"])
