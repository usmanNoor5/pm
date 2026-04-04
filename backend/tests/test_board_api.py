from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import login


def test_startup_creates_database_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "created-on-startup.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200

    assert db_path.exists()


def test_get_board_requires_auth(client: TestClient) -> None:
    response = client.get("/api/board")
    assert response.status_code == 401


def test_get_board_returns_seeded_data_when_authenticated(client: TestClient) -> None:
    login(client)
    response = client.get("/api/board")
    assert response.status_code == 200

    payload = response.json()
    assert "board" in payload
    assert len(payload["board"]["columns"]) == 5
    assert "card-1" in payload["board"]["cards"]


def test_update_board_persists_changes(client: TestClient) -> None:
    login(client)

    board_response = client.get("/api/board")
    board = board_response.json()["board"]
    board["columns"][0]["title"] = "Inbox"

    update_response = client.put("/api/board", json={"board": board})
    assert update_response.status_code == 200
    assert update_response.json()["board"]["columns"][0]["title"] == "Inbox"

    read_back_response = client.get("/api/board")
    assert read_back_response.status_code == 200
    assert read_back_response.json()["board"]["columns"][0]["title"] == "Inbox"


def test_update_board_rejects_missing_card_reference(client: TestClient) -> None:
    login(client)

    board_response = client.get("/api/board")
    board = board_response.json()["board"]
    board["columns"][0]["cardIds"].append("card-does-not-exist")

    response = client.put("/api/board", json={"board": board})
    assert response.status_code == 422
