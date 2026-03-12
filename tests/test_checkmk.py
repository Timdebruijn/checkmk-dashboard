"""
Tests for checkmk.py – unit tests that do not require a live Checkmk instance.
All HTTP calls are intercepted with pytest-httpx (or httpx mock transport).
"""

import importlib
import os
import sys
import pytest
import httpx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_checkmk(**env_overrides):
    """(Re-)import checkmk with the given environment variables set."""
    for key, value in env_overrides.items():
        os.environ[key] = value
    # Remove cached module so load_dotenv / os.getenv picks up new values
    sys.modules.pop("checkmk", None)
    import checkmk as mod
    return mod


# ---------------------------------------------------------------------------
# _has_ticket
# ---------------------------------------------------------------------------

class TestHasTicket:
    def test_ticket_present_exact_case(self):
        mod = _reload_checkmk(TICKET_PATTERN="INC")
        assert mod._has_ticket("INC0012345 – disk full") is True

    def test_ticket_present_lowercase(self):
        mod = _reload_checkmk(TICKET_PATTERN="INC")
        assert mod._has_ticket("inc9999 problem acknowledged") is True

    def test_ticket_absent(self):
        mod = _reload_checkmk(TICKET_PATTERN="INC")
        assert mod._has_ticket("no ticket here") is False

    def test_custom_pattern(self):
        mod = _reload_checkmk(TICKET_PATTERN="CHG")
        assert mod._has_ticket("CHG001 change window") is True
        assert mod._has_ticket("INC001 ignored") is False


# ---------------------------------------------------------------------------
# get_problems – mocked HTTP responses
# ---------------------------------------------------------------------------

MOCK_SERVICES = [
    # Critical, unacknowledged
    {
        "extensions": {
            "host_name": "server01",
            "description": "CPU load",
            "state": 2,
            "plugin_output": "CRIT - load 95%",
            "acknowledged": 0,
            "comments_with_info": [],
            "last_state_change": "2024-01-01T00:00:00Z",
        }
    },
    # Warning, unacknowledged
    {
        "extensions": {
            "host_name": "server02",
            "description": "Disk /var",
            "state": 1,
            "plugin_output": "WARN - 85% used",
            "acknowledged": 0,
            "comments_with_info": [],
            "last_state_change": "2024-01-01T01:00:00Z",
        }
    },
    # Critical but acknowledged with ticket
    {
        "extensions": {
            "host_name": "server03",
            "description": "Memory",
            "state": 2,
            "plugin_output": "CRIT - memory 99%",
            "acknowledged": 1,
            "comments_with_info": [["user", "2024-01-01", "INC0099 – investigating"]],
            "last_state_change": "2024-01-01T02:00:00Z",
        }
    },
    # Acknowledged but without a ticket → should fall into warning bucket
    {
        "extensions": {
            "host_name": "server04",
            "description": "Network",
            "state": 1,
            "plugin_output": "WARN - packet loss",
            "acknowledged": 1,
            "comments_with_info": [["user", "2024-01-01", "checking"]],
            "last_state_change": "2024-01-01T03:00:00Z",
        }
    },
]


class MockTransport(httpx.AsyncBaseTransport):
    """Returns a canned JSON response for any request."""

    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self._status_code = status_code

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        import json
        return httpx.Response(
            self._status_code,
            headers={"Content-Type": "application/json"},
            content=json.dumps(self._payload).encode(),
        )


async def test_get_problems_categorises_services(monkeypatch):
    mod = _reload_checkmk(
        CMK_URL="http://mock-checkmk.example.com/site",
        CMK_USER="automation",
        CMK_SECRET="dummy",
        CMK_SITE="",
        TICKET_PATTERN="INC",
    )

    transport = MockTransport({"value": MOCK_SERVICES})

    # Patch AsyncClient to use our mock transport
    original_client = httpx.AsyncClient

    def patched_client(**kwargs):
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    result = await mod.get_problems()

    assert len(result["critical"]) == 1
    assert result["critical"][0]["host"] == "server01"

    assert len(result["warning"]) == 2  # server02 + server04 (ack without ticket)
    warning_hosts = {w["host"] for w in result["warning"]}
    assert "server02" in warning_hosts
    assert "server04" in warning_hosts

    assert len(result["acknowledged"]) == 1
    assert result["acknowledged"][0]["host"] == "server03"


async def test_get_problems_raises_on_http_error(monkeypatch):
    mod = _reload_checkmk(
        CMK_URL="http://mock-checkmk.example.com/site",
        CMK_USER="automation",
        CMK_SECRET="dummy",
        CMK_SITE="",
    )

    transport = MockTransport({}, status_code=503)

    original_client = httpx.AsyncClient

    def patched_client(**kwargs):
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    with pytest.raises(httpx.HTTPStatusError):
        await mod.get_problems()
