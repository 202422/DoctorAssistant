"""Google Maps MCP Client via Smithery (sync).

This module mirrors the pattern used by ``neon_client.py`` but targets the
Google Maps MCP instance configured via the ``MAP_SMITHERY_*`` environment
variables.  It provides a synchronous client for calling MCP tools exposed by
that service (e.g. geocoding, directions, distance matrix, etc.).

Usage is analogous to the Neon MCP client:

```python
from doctor_assistant.mcp.google_map_client import GoogleMapsMCPClient

client = GoogleMapsMCPClient()
response = client.call_tool("geocode", {"address": "1600 Amphitheatre Parkway, Mountain View, CA"})
```

Feel free to expand this class with domain-specific helper methods once the
MCP toolset is known.
"""

import json
import time
import logging
import httpx

from typing import Optional

from ..utils import get_logger
from ..config import settings

logger = get_logger(__name__)


# ============================================================
# GOOGLE MAPS MCP CLIENT (sync)
# ============================================================

class GoogleMapsMCPClient:
    """Synchronous client for Google Maps via Smithery MCP.

    The client reads its base URL and API key from the ``settings``
    attributes ``MAP_SMITHERY_MCP_URL`` and ``MAP_SMITHERY_API_KEY``.
    """

    def __init__(self):
        # prefer the explicit map settings, falling back to an empty string if
        # they were not provided (the MCP will then likely reject calls).
        self.base_url = settings.MAP_SMITHERY_MCP_URL
        self.api_key = settings.MAP_SMITHERY_API_KEY

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

        self.logger = logging.getLogger(__name__)

        # Persistent synchronous HTTP client
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=15.0,   # was 15.0
        read=10.0,     
        write=10.0,    
        pool=5.0       
            ),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5
            )
        )

    def __del__(self):
        """Close HTTP client on garbage collection."""
        try:
            self._client.close()
        except Exception:
            pass

    # -----------------------------
    # SSE PARSING
    # -----------------------------

    def parse_sse_json(self, response_text: str):
        """Extract JSON from an SSE-style MCP response."""
        for line in response_text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                json_part = line[len("data:"):].strip()
                try:
                    return json.loads(json_part)
                except json.JSONDecodeError:
                    return json_part
        return response_text

    # -----------------------------
    # MCP TOOL CALL (sync) - WITH RETRY
    # -----------------------------

    def call_tool(self, tool_name: str, arguments: dict, max_retries: int = 2):
        """Call an MCP tool with simple retry logic for timeouts.

        Parameters
        ----------
        tool_name : str
            Name of the tool to invoke (defined by the MCP server).
        arguments : dict
            JSON-serializable arguments to pass.
        max_retries : int
            Number of attempts to make if the request times out.

        Returns
        -------
        Any
            The parsed result from the MCP service (often a dict).
        """

        last_error = None
        for attempt in range(max_retries):
            try:
                self.logger.info(f"🔧 Calling Map MCP tool: {tool_name} (attempt {attempt+1}/{max_retries})")

                payload = {
                    "jsonrpc": "2.0",
                    "id": str(time.time()),
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                }

                response = self._client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )

                self.logger.debug(f"STATUS: {response.status_code}")
                self.logger.debug(f"RAW RESPONSE: {response.text[:1000]}")

                if response.status_code != 200:
                    raise Exception(f"MCP call failed: {response.status_code} - {response.text}")

                result = self.parse_sse_json(response.text)

                # if the MCP returned a JSON string (encoded twice) decode it
                if isinstance(result, str):
                    try:
                        candidate = json.loads(result)
                        result = candidate
                    except json.JSONDecodeError:
                        pass

                # handle plain string responses gracefully (older MCPs or simple tools)
                if not isinstance(result, dict):
                    return result

                if "error" in result:
                    raise Exception(result["error"])

                inner = result.get("result", {})
                content = inner.get("content", [])
                if content and isinstance(content[0], dict) and content[0].get("type") == "text":
                    text = content[0]["text"]
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
                return inner

            except httpx.ReadTimeout as e:
                last_error = e
                self.logger.warning(f"Timeout calling {tool_name}, retrying... ({attempt+1})")
                continue

        # if we fall through, re-raise the last error
        raise last_error if last_error is not None else Exception("Unknown error")



# ============================================================
# GLOBAL CLIENT INSTANCE
# ============================================================

_map_client: Optional[GoogleMapsMCPClient] = None


def get_google_maps_client() -> GoogleMapsMCPClient:
    """Return a singleton Google Maps MCP client."""
    global _map_client
    if _map_client is None:
        _map_client = GoogleMapsMCPClient()
    return _map_client


# Quick sanity test when executed directly
if __name__ == "__main__":
    client = get_google_maps_client()
    print("Base URL:", client.base_url)
    print("API key set:", bool(client.api_key))
    # Example placeholder call (fail if no credentials provided)
    try:
        res = client.call_tool("text_search", {"textQuery":"casanearshore"})
        print("Result:", res)
        # if the response still contains a nested 'result' key, unwrap it for
        # readability
        if isinstance(res, dict) and "result" in res:
            print("Unwrapped result:", res["result"])
    except Exception as exc:
        print("Tool call failed (expected if no config):", exc)
