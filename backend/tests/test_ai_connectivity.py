import os

import pytest
from fastapi.testclient import TestClient

from app.ai import AiServiceError
from app.main import app
from tests.conftest import login


def test_ai_ping_requires_auth(client: TestClient) -> None:
    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 401


def test_ai_ping_returns_503_without_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    login(client)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["ok"] is False
    assert payload["response"] is None
    assert "OPENROUTER_API_KEY" in payload["error"]


def test_ai_ping_returns_502_on_service_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    login(client)

    async def fail_request(_: str):
        raise AiServiceError("OpenRouter request failed")

    monkeypatch.setattr("app.main.request_ai_message", fail_request)
    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 502
    payload = response.json()
    assert payload["ok"] is False
    assert payload["response"] is None
    assert payload["error"] == "OpenRouter request failed"


def test_ai_ping_success_with_mock(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    login(client)

    class MockReply:
        ok = True
        model = "qwen/qwen3.6-plus:free"
        response = "4"
        error = None

    async def mock_request(_: str) -> MockReply:
        return MockReply()

    monkeypatch.setattr("app.main.request_ai_message", mock_request)

    response = client.post("/api/ai/ping", json={"question": "2+2"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["response"] == "4"
    assert payload["error"] is None
    assert payload["model"] == "qwen/qwen3.6-plus:free"


@pytest.mark.integration
def test_ai_ping_live_connectivity_opt_in(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    if os.getenv("ENABLE_OPENROUTER_CONNECTIVITY_TEST") != "1":
        pytest.skip("Set ENABLE_OPENROUTER_CONNECTIVITY_TEST=1 to run live OpenRouter connectivity test")

    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY is required for live OpenRouter connectivity test")

    login(client)
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus:free")
    response = client.post("/api/ai/ping", json={"question": "2+2"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["model"] == "qwen/qwen3.6-plus:free"
    assert isinstance(payload["response"], str)
    assert payload["response"].strip() != ""
    assert payload["error"] is None
