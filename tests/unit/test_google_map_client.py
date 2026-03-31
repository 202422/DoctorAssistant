import pytest

from doctor_assistant.mcp.google_map_client import GoogleMapsMCPClient


class _FakeTool:
    def __init__(self, name, result=None, error=None):
        self.name = name
        self._result = result
        self._error = error

    async def ainvoke(self, arguments):
        if self._error is not None:
            raise self._error
        return self._result


class _FakeMCPClient:
    def __init__(self, tools):
        self._tools = tools

    async def get_tools(self, server_name=None):
        return self._tools


def _build_client(monkeypatch, tools):
    from doctor_assistant.config import settings

    monkeypatch.setattr(settings, "MAP_SMITHERY_MCP_URL", "https://example.com/mcp")
    monkeypatch.setattr(settings, "MAP_SMITHERY_API_KEY", "test-key")
    monkeypatch.setattr(settings, "MAP_MCP_TRANSPORT", "sse")

    client = GoogleMapsMCPClient()
    client._mcp_client = _FakeMCPClient(tools)
    return client


def test_call_tool_parses_text_json(monkeypatch):
    tool = _FakeTool(
        "text_search",
        result=([{"type": "text", "text": '{"places": [{"name": "Pharmacy A"}]}' }], None),
    )
    client = _build_client(monkeypatch, [tool])

    result = client.call_tool("text_search", {"textQuery": "pharmacy near me"})

    assert isinstance(result, dict)
    assert result["places"][0]["name"] == "Pharmacy A"


def test_call_tool_retries_then_succeeds(monkeypatch):
    calls = {"count": 0}

    class _FlakyTool:
        name = "nearby_search"

        async def ainvoke(self, arguments):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary MCP failure")
            return ([{"type": "text", "text": "ok"}], None)

    client = _build_client(monkeypatch, [_FlakyTool()])

    result = client.call_tool("nearby_search", {"latitude": 1.0, "longitude": 2.0, "radius": 1000})

    assert result == "ok"
    assert calls["count"] == 2


def test_call_tool_raises_for_unknown_tool(monkeypatch):
    client = _build_client(monkeypatch, [])

    with pytest.raises(ValueError, match="tool 'missing_tool' not found"):
        client.call_tool("missing_tool", {})
