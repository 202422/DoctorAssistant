"""LangChain tools wrapping the synchronous Google Maps MCP client.

The pattern mirrors ``neon_tools.py`` but points at the Google Maps MCP
instance.  Tools now use StructuredTool + Pydantic schemas so LangGraph
can correctly bind multiple arguments (no more "Too many arguments to
single-input tool" error).

Tools available:
* ``nearby_search`` – radius/latitude/longitude search with various filters.
* ``text_search`` – full‑text place search.
"""

from src.doctor_assistant.mcp.google_map_client import get_google_maps_client
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Pydantic input schemas (this is what fixes the LangGraph error)
# ---------------------------------------------------------------------------

class NearbySearchInput(BaseModel):
    """Input for nearby_search tool (Google Places Nearby Search)."""
    latitude: float = Field(..., description="Latitude coordinate of the center point")
    longitude: float = Field(..., description="Longitude coordinate of the center point")
    radius: int = Field(..., description="Radius in meters defining the circular search area (max 50000)")
    includedTypes: Optional[List[str]] = Field(
        None, description="Place types to include (e.g. ['pharmacy']). Results must match at least one."
    )
    excludedTypes: Optional[List[str]] = Field(
        None, description="Place types to exclude (e.g. ['cafe'])."
    )
    maxResultCount: Optional[int] = Field(10, description="Maximum number of results to return (default 10)")
    fieldMask: Optional[str] = Field(
        None, description="Comma-separated fields to return (e.g. 'places.displayName,places.formattedAddress')"
    )


class TextSearchInput(BaseModel):
    """Input for text_search tool (Google Places Text Search)."""
    textQuery: str = Field(..., description="The text query to search for (e.g. 'pharmacies near Casablanca')")
    locationBias: Optional[dict] = Field(
        None, description="Optional location bias as {'latitude': float, 'longitude': float}"
    )
    maxResultCount: Optional[int] = Field(10, description="Maximum number of results")


# ---------------------------------------------------------------------------
# Tool functions (now receive structured data, no manual json.loads)
# ---------------------------------------------------------------------------

def nearby_search_tool(
    latitude: float,
    longitude: float,
    radius: int,
    includedTypes: Optional[List[str]] = None,
    excludedTypes: Optional[List[str]] = None,
    maxResultCount: int = 10,
    fieldMask: Optional[str] = None,
) -> str:
    """Search for places near a location using Google Maps MCP."""
    client = get_google_maps_client()

    args = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "maxResultCount": maxResultCount,
    }
    print(f"Tool call: nearby_search with args: {args}")
    if includedTypes:
        args["includedTypes"] = includedTypes
    if excludedTypes:
        args["excludedTypes"] = excludedTypes
    if fieldMask:
        args["fieldMask"] = fieldMask

    result = client.call_tool("nearby_search", args)

    print(f"Tool result: {result}")

    return str(result)


def text_search_tool(
    textQuery: str,
    locationBias: Optional[dict] = None,
    maxResultCount: int = 10,
) -> str:
    """Full-text place search using Google Maps MCP."""
    client = get_google_maps_client()
    args = {
        "textQuery": textQuery,
        "maxResultCount": maxResultCount,
    }
    if locationBias:
        args["locationBias"] = locationBias

    result = client.call_tool("text_search", args)
    return str(result)

# ---------------------------------------------------------------------------
# Tool collection (StructuredTool instances)
# ---------------------------------------------------------------------------

google_map_tools = [
    StructuredTool.from_function(
        func=nearby_search_tool,
        name="nearby_search",
        description=(
            """Search for places (e.g., restaurants, parks) within a specified circular area.

The input must be a JSON object with the following required keys:

- ``radius`` (number) – required. Radius in meters defining the circular search area.
- ``latitude`` (number) – required. Latitude coordinate of the center point.
- ``longitude`` (number) – required. Longitude coordinate of the center point.

Optional keys:

- ``fieldMask`` (string) – Specifies which fields to return in the response (e.g., 'places.displayName').
- ``excludedTypes`` (array of strings) – Place types to exclude (e.g., 'cafe').
- ``includedTypes`` (array of strings) – Place types to include (e.g., 'restaurant', 'pharmacy').
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
        args_schema=NearbySearchInput,
    ),

    StructuredTool.from_function(
        func=text_search_tool,
        name="text_search",
        description=(
            """Perform a full-text place search using a query string.

The input must be a JSON object with:

Required:
- ``textQuery`` (string) – The search query (e.g., "pharmacies near Casablanca").

Optional:
- ``locationBias`` (object) – Bias results toward a location:
    {
        "latitude": float,
        "longitude": float
    }
- ``maxResultCount`` (integer) – Maximum number of results to return. Default is 10.

Example input:
{
    "textQuery": "pharmacies near Casablanca",
    "maxResultCount": 5
}
"""
        ),
        args_schema=TextSearchInput,
    ),
]