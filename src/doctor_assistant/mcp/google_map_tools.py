"""
Google Maps Tools Module for Doctor Assistant Multi-Agent System.

Provides LangChain-compatible tools for the PharmacyFinder agent to
search for pharmacies and other medical facilities.

Tools:
- nearby_search: Find places within a radius (lat/lng based)
- text_search: Find places by text query (e.g., "pharmacies near X")

Note: Uses StructuredTool + Pydantic schemas to support multiple
arguments in LangGraph (fixes "Too many arguments" error).
"""

from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .google_map_client import get_google_maps_client


# =============================================================================
# PYDANTIC INPUT SCHEMAS
# =============================================================================
# These schemas enable LangGraph to correctly parse multi-argument tool calls.
# Without them, LangGraph throws "Too many arguments to single-input tool".

class NearbySearchInput(BaseModel):
    """
    Schema for nearby_search tool.
    
    Searches for places within a circular area defined by
    center coordinates (lat/lng) and radius.
    """
    latitude: float = Field(
        ...,
        description="Latitude of search center point",
    )
    longitude: float = Field(
        ...,
        description="Longitude of search center point",
    )
    radius: int = Field(
        ...,
        description="Search radius in meters (max 50000)",
    )
    includedTypes: Optional[List[str]] = Field(
        None,
        description="Place types to include (e.g., ['pharmacy', 'hospital'])",
    )
    excludedTypes: Optional[List[str]] = Field(
        None,
        description="Place types to exclude (e.g., ['cafe'])",
    )
    maxResultCount: Optional[int] = Field(
        10,
        description="Max results to return (default: 10)",
    )
    fieldMask: Optional[str] = Field(
        None,
        description="Fields to return (e.g., 'places.displayName,places.formattedAddress')",
    )


class TextSearchInput(BaseModel):
    """
    Schema for text_search tool.
    
    Searches for places using natural language query
    (e.g., "pharmacies near Casablanca").
    """
    textQuery: str = Field(
        ...,
        description="Search query (e.g., 'pharmacies near Casablanca')",
    )
    locationBias: Optional[dict] = Field(
        None,
        description="Bias results toward location: {'latitude': float, 'longitude': float}",
    )
    maxResultCount: Optional[int] = Field(
        10,
        description="Max results to return (default: 10)",
    )


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def nearby_search_tool(
    latitude: float,
    longitude: float,
    radius: int,
    includedTypes: Optional[List[str]] = None,
    excludedTypes: Optional[List[str]] = None,
    maxResultCount: int = 10,
    fieldMask: Optional[str] = None,
) -> str:
    """
    Search for places near a geographic point.
    
    Used by PharmacyFinder agent to find pharmacies near
    a patient's location using coordinates.
    
    Returns:
        JSON string of matching places.
    """
    client = get_google_maps_client()

    # Build required arguments
    args = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "maxResultCount": maxResultCount,
    }

    print(f"Tool call: nearby_search with args: {args}")

    # Add optional filters if provided
    if includedTypes:
        args["includedTypes"] = includedTypes
    if excludedTypes:
        args["excludedTypes"] = excludedTypes
    if fieldMask:
        args["fieldMask"] = fieldMask

    # Call MCP and return result
    result = client.call_tool("nearby_search", args)
    print(f"Tool result: {result}")

    return str(result)


def text_search_tool(
    textQuery: str,
    locationBias: Optional[dict] = None,
    maxResultCount: int = 10,
) -> str:
    """
    Search for places using natural language query.
    
    Used by PharmacyFinder agent when patient provides
    an address or area name instead of coordinates.
    
    Returns:
        JSON string of matching places.
    """
    client = get_google_maps_client()

    # Build arguments
    args = {
        "textQuery": textQuery,
        "maxResultCount": maxResultCount,
    }

    # Add location bias if provided (improves relevance)
    if locationBias:
        args["locationBias"] = locationBias

    # Call MCP and return result
    result = client.call_tool("text_search", args)

    return str(result)


# =============================================================================
# TOOL DEFINITIONS (exported for agent binding)
# =============================================================================

google_map_tools = [
    # -------------------------------------------------------------------------
    # NEARBY SEARCH TOOL
    # -------------------------------------------------------------------------
    StructuredTool.from_function(
        func=nearby_search_tool,
        name="nearby_search",
        description="""Search for places within a circular area around coordinates.

Required parameters:
- latitude (float): Center point latitude
- longitude (float): Center point longitude  
- radius (int): Search radius in meters (max 50000)

Optional parameters:
- includedTypes (list): Place types to include, e.g., ["pharmacy"]
- excludedTypes (list): Place types to exclude, e.g., ["cafe"]
- maxResultCount (int): Max results (default: 10)
- fieldMask (str): Fields to return

Example:
{
    "latitude": 37.7749,
    "longitude": -122.4194,
    "radius": 1000,
    "includedTypes": ["pharmacy"],
    "maxResultCount": 5
}""",
        args_schema=NearbySearchInput,
    ),

    # -------------------------------------------------------------------------
    # TEXT SEARCH TOOL
    # -------------------------------------------------------------------------
    StructuredTool.from_function(
        func=text_search_tool,
        name="text_search",
        description="""Search for places using a text query.

Required parameters:
- textQuery (str): Natural language search query

Optional parameters:
- locationBias (dict): Bias toward location {"latitude": float, "longitude": float}
- maxResultCount (int): Max results (default: 10)

Example:
{
    "textQuery": "pharmacies near Casablanca",
    "maxResultCount": 5
}""",
        args_schema=TextSearchInput,
    ),
]