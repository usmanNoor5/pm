from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai import AiServiceError
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ai.db"))
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_ai_ping_requires_auth(client: TestClient) -> None:
    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 401


def test_ai_ping_returns_503_without_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(client)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_ai_ping_returns_502_on_service_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(client)

    def fail_request(_: str):
        raise AiServiceError("OpenRouter request failed")

    monkeypatch.setattr("app.main.request_ai_message", fail_request)
    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 502


def test_ai_ping_success_with_mock(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _login(client)

    class MockReply:
        model = "qwen/qwen3.6-plus-preview:free"
        answer = "4"

    monkeypatch.setattr("app.main.request_ai_message", lambda _: MockReply())

    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "2+2"
    assert payload["answer"] == "4"
    assert payload["model"] == "qwen/qwen3.6-plus-preview:free"
