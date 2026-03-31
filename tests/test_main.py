import os

from fastapi.testclient import TestClient

# Set required env vars before importing main
os.environ["CMK_URL"] = "http://mock-checkmk.example.com/site"
os.environ["CMK_USER"] = "automation"
os.environ["CMK_SECRET"] = "dummy-secret"
os.environ["CMK_SITE"] = ""
os.environ["TICKET_PATTERN"] = "INC"
os.environ["DASHBOARD_USER"] = ""
os.environ["DASHBOARD_PASSWORD"] = ""

import main as main_module
from main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Root route
# ---------------------------------------------------------------------------

def test_root_returns_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# /api/config
# ---------------------------------------------------------------------------

def test_config_defaults():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "site" in data
    assert "support_email" in data
    assert "support_phone" in data
    assert "logo" in data


# ---------------------------------------------------------------------------
# /api/problems  (mocked get_problems)
# ---------------------------------------------------------------------------

def test_problems_returns_structure(monkeypatch):
    async def mock_get_problems():
        return {"critical": [], "warning": [], "acknowledged": []}

    monkeypatch.setattr(main_module, "get_problems", mock_get_problems)

    response = client.get("/api/problems")
    assert response.status_code == 200
    data = response.json()
    assert "critical" in data
    assert "warning" in data
    assert "acknowledged" in data


def test_problems_500_on_exception(monkeypatch):
    async def mock_get_problems():
        raise RuntimeError("connection failed")

    monkeypatch.setattr(main_module, "get_problems", mock_get_problems)

    response = client.get("/api/problems")
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Basic auth – patches module-level variables directly
# ---------------------------------------------------------------------------

def test_auth_required_when_credentials_set():
    original_auth_enabled = main_module._auth_enabled
    original_user = main_module._AUTH_USER
    original_pass = main_module._AUTH_PASSWORD

    main_module._auth_enabled = True
    main_module._AUTH_USER = "admin"
    main_module._AUTH_PASSWORD = "secret"

    try:
        response = client.get("/api/config")
        assert response.status_code == 401
    finally:
        main_module._auth_enabled = original_auth_enabled
        main_module._AUTH_USER = original_user
        main_module._AUTH_PASSWORD = original_pass


def test_auth_succeeds_with_correct_credentials():
    original_auth_enabled = main_module._auth_enabled
    original_user = main_module._AUTH_USER
    original_pass = main_module._AUTH_PASSWORD

    main_module._auth_enabled = True
    main_module._AUTH_USER = "admin"
    main_module._AUTH_PASSWORD = "secret"

    try:
        response = client.get("/api/config", auth=("admin", "secret"))
        assert response.status_code == 200
    finally:
        main_module._auth_enabled = original_auth_enabled
        main_module._AUTH_USER = original_user
        main_module._AUTH_PASSWORD = original_pass
