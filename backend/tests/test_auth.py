from fastapi.testclient import TestClient

from app.main import app


def test_health_route() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_me_is_false_before_login() -> None:
    client = TestClient(app)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "username": None}


def test_login_rejects_invalid_credentials() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"username": "wrong", "password": "creds"},
    )
    assert response.status_code == 401


def test_login_sets_cookie_and_logout_clears_session() -> None:
    client = TestClient(app)

    login_response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login_response.status_code == 200
    assert login_response.json() == {"authenticated": True, "username": "user"}
    assert "pm_session" in login_response.cookies

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == {"authenticated": True, "username": "user"}

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"authenticated": False, "username": None}

    after_logout_response = client.get("/api/auth/me")
    assert after_logout_response.status_code == 200
    assert after_logout_response.json() == {"authenticated": False, "username": None}
