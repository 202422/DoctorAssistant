"""LangChain tools wrapping the synchronous Google Maps MCP client.

The pattern mirrors ``neon_tools.py`` but points at the Google Maps MCP
instance.  Each tool expects a JSON-encoded string as its single argument; the
string is parsed into a dictionary and forwarded to the underlying client.

Tools available:

* ``nearby_search`` – radius/latitude/longitude search with various filters.
* ``text_search`` – full‑text place search.

Example usage from an LLM prompt (LangChain will handle the JSON formatting):

```
{"radius":1000,"latitude":37.42,"longitude":-122.08,"includedTypes":["restaurant"]}
```
"""

import json

from src.doctor_assistant.mcp.google_map_client import get_google_maps_client
from langchain_core.tools import Tool


# ---------------------------------------------------------------------------
# Wrappers
# ---------------------------------------------------------------------------

def nearby_search_tool(input_str: str) -> str:
    client = get_google_maps_client()
    try:
        args = json.loads(input_str)
    except Exception as e:
        return f"❌ Invalid JSON input: {e}"

    result = client.call_tool("nearby_search", args)
    return str(result)

def text_search_tool(input_str: str) -> str:
    client = get_google_maps_client()
    try:
        args = json.loads(input_str)
    except Exception as e:
        return f"❌ Invalid JSON input: {e}"

    result = client.call_tool("text_search", args)
    return str(result)


# ---------------------------------------------------------------------------
# Tool collection
# ---------------------------------------------------------------------------

google_map_tools = [
    Tool(
        name="nearby_search",
        func=nearby_search_tool,
        description=(
            """Search for places (e.g., restaurants, parks) within a specified circular area.

    The input must be a JSON object with the following required keys:

    - ``radius`` (number) – required. Radius in meters defining the circular search area.
    - ``latitude`` (number) – required. Latitude coordinate of the center point.
    - ``longitude`` (number) – required. Longitude coordinate of the center point.

    Optional keys:

    - ``fieldMask`` (string) – Specifies which fields to return in the response (e.g., 'places.displayName'). Use to customize the data payload.
    - ``excludedTypes`` (array of strings) – Place types to exclude (e.g., 'cafe', 'store'); results matching any of these types are omitted. See Google Maps Places API documentation for supported types. Example: ["cafe"].
    - ``includedTypes`` (array of strings) – Place types to include (e.g., 'restaurant', 'park', 'pharmacy'); results will match at least one of these types. See Google Maps Places API documentation for supported types. Example: ["restaurant"].
    - ``maxResultCount`` (integer) – Maximum number of results to return. Default is 10.

    Example input:
    {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 1000,
        "includedTypes": ["pharmacy"],
        "maxResultCount": 5
    }
    """
        ),
    )
]
