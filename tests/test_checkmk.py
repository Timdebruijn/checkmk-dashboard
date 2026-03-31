import importlib
import json

import httpx
import pytest

# Will be set up by the autouse fixture before each test
checkmk = None


@pytest.fixture(autouse=True)
def _set_checkmk_env(monkeypatch):
    monkeypatch.setenv("CMK_URL", "http://mock-checkmk.example.com/site")
    monkeypatch.setenv("CMK_USER", "automation")
    monkeypatch.setenv("CMK_SECRET", "dummy-secret")
    monkeypatch.setenv("CMK_SITE", "")
    monkeypatch.setenv("TICKET_PATTERN", "INC")

    import checkmk as _checkmk
    importlib.reload(_checkmk)

    global checkmk
    checkmk = _checkmk


# ---------------------------------------------------------------------------
# _has_ticket
# ---------------------------------------------------------------------------

class TestHasTicket:
    def test_matching_prefix_returns_true(self):
        assert checkmk._has_ticket("INC0001234 outage") is True

    def test_case_insensitive(self):
        assert checkmk._has_ticket("inc0001234 outage") is True

    def test_no_ticket_returns_false(self):
        assert checkmk._has_ticket("no ticket here") is False

    def test_empty_comment_returns_false(self):
        assert checkmk._has_ticket("") is False

    def test_partial_match_at_end(self):
        assert checkmk._has_ticket("See INC9999") is True


# ---------------------------------------------------------------------------
# get_problems – mocked HTTP transport
# ---------------------------------------------------------------------------

def _make_service(host, description, state, acknowledged=False, comments=None):
    """Helper to build a Checkmk-like service entry."""
    return {
        "extensions": {
            "host_name": host,
            "description": description,
            "state": state,
            "plugin_output": f"{description} output",
            "acknowledged": acknowledged,
            "comments_with_info": comments or [],
            "last_state_change": "2024-01-01T00:00:00Z",
        }
    }


MOCK_RESPONSE = {
    "value": [
        _make_service("host1", "CPU load", 2),                          # critical
        _make_service("host2", "Disk space", 1),                        # warning
        _make_service(                                                    # acknowledged w/ ticket
            "host3", "Memory", 2, acknowledged=True,
            comments=[["author", "time", "INC0001 acknowledged"]]
        ),
        _make_service(                                                    # ack w/o ticket → critical
            "host4", "Network", 2, acknowledged=True,
            comments=[["author", "time", "just a note"]]
        ),
    ]
}


class MockTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        body = json.dumps(MOCK_RESPONSE).encode()
        return httpx.Response(200, content=body, headers={"Content-Type": "application/json"}, request=request)


@pytest.mark.asyncio
async def test_get_problems_categories(monkeypatch):
    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = MockTransport()
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", PatchedClient)
    result = await checkmk.get_problems()

    assert len(result["critical"]) == 2      # host1 (state 2) + host4 (ack w/o ticket, state 2)
    assert len(result["warning"]) == 1       # host2 (state 1)
    assert len(result["acknowledged"]) == 1  # host3 (ack with INC ticket)


@pytest.mark.asyncio
async def test_get_problems_raises_on_error(monkeypatch):
    class ErrorTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(500, content=b"Internal Server Error", request=request)

    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = ErrorTransport()
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", PatchedClient)
    with pytest.raises(httpx.HTTPStatusError):
        await checkmk.get_problems()
