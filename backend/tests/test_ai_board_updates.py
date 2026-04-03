import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai_board import parse_ai_structured_output
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ai-board.db"))
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_parse_ai_structured_output_valid_payload() -> None:
    payload = {
        "response": "Done.",
        "board": {
            "columns": [
                {"id": "col-1", "title": "Backlog", "cardIds": ["card-1"]},
            ],
            "cards": {
                "card-1": {"id": "card-1", "title": "Task", "details": "Details"},
            },
        },
    }

    response, board, fallback_used, error = parse_ai_structured_output(json.dumps(payload))

    assert response == "Done."
    assert board is not None
    assert board.columns[0].title == "Backlog"
    assert fallback_used is False
    assert error is None


def test_parse_ai_structured_output_invalid_schema_fallback() -> None:
    bad_payload = {
        "response": "Will update",
        "board": {"columns": [], "cards": {}},
        "unexpected": "extra",
    }

    response, board, fallback_used, error = parse_ai_structured_output(json.dumps(bad_payload))

    assert response != ""
    assert board is None
    assert fallback_used is True
    assert error == "AI output did not match required schema; board unchanged"


def test_ai_chat_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/ai/chat",
        json={"message": "Move a card", "history": []},
    )
    assert response.status_code == 401


def test_ai_chat_response_only_no_board_update(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(client)

    class MockReply:
        ok = True
        model = "qwen/qwen3.6-plus:free"
        response = json.dumps({"response": "No board changes needed", "board": None})
        error = None

    monkeypatch.setattr("app.main.request_ai_message", lambda _: MockReply())

    before = client.get("/api/board").json()["board"]
    response = client.post(
        "/api/ai/chat",
        json={
            "message": "Any suggestions?",
            "history": [{"role": "user", "content": "How can I improve focus?"}],
        },
    )
    after = client.get("/api/board").json()["board"]

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["response"] == "No board changes needed"
    assert payload["boardUpdated"] is False
    assert payload["fallbackUsed"] is False
    assert payload["board"] is None
    assert payload["error"] is None
    assert before == after


def test_ai_chat_valid_board_update_applies_transactionally(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(client)

    current_board = client.get("/api/board").json()["board"]
    updated_board = json.loads(json.dumps(current_board))
    updated_board["columns"][0]["title"] = "AI Updated Backlog"

    class MockReply:
        ok = True
        model = "qwen/qwen3.6-plus:free"
        response = json.dumps(
            {
                "response": "Renamed Backlog column.",
                "board": updated_board,
            }
        )
        error = None

    monkeypatch.setattr("app.main.request_ai_message", lambda _: MockReply())

    response = client.post(
        "/api/ai/chat",
        json={"message": "Rename backlog to AI Updated Backlog", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["boardUpdated"] is True
    assert payload["fallbackUsed"] is False
    assert payload["board"]["columns"][0]["title"] == "AI Updated Backlog"

    read_back = client.get("/api/board").json()["board"]
    assert read_back["columns"][0]["title"] == "AI Updated Backlog"


def test_ai_chat_malformed_payload_uses_fallback_without_board_change(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(client)

    class MockReply:
        ok = True
        model = "qwen/qwen3.6-plus:free"
        response = "I think you should move one task to review."
        error = None

    monkeypatch.setattr("app.main.request_ai_message", lambda _: MockReply())

    before = client.get("/api/board").json()["board"]
    response = client.post(
        "/api/ai/chat",
        json={"message": "Any update?", "history": []},
    )
    after = client.get("/api/board").json()["board"]

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["boardUpdated"] is False
    assert payload["fallbackUsed"] is True
    assert payload["board"] is None
    assert payload["response"] == "I think you should move one task to review."
    assert payload["error"] == "AI output was not valid JSON; board unchanged"
    assert before == after
