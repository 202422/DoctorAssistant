"""
Google Maps Tools Module for Doctor Assistant Multi-Agent System.

Provides LangChain-compatible tools for the PharmacyFinder agent by
loading them directly from the Google Maps MCP server via
langchain-mcp-adapters.

Tools are auto-discovered from the MCP server — no manual StructuredTool
definitions or Pydantic schemas needed. The MCP server itself advertises:
- nearby_search: Find places within a radius (lat/lng based)
- text_search:   Find places by text query (e.g., "pharmacies near X")

Usage (async context required):
    tools = await get_google_map_tools()
    # Pass `tools` to your LangGraph agent / ToolNode
"""

import asyncio
from typing import List

from langchain_core.tools import BaseTool

from .google_map_client import get_google_maps_client
from ..utils import get_logger


logger = get_logger(__name__)


# =============================================================================
# TOOL LOADER
# =============================================================================

async def get_google_map_tools() -> List[BaseTool]:
    """
    Load Google Maps tools from the MCP server.

    Connects to the Smithery MCP endpoint and converts all exposed
    MCP tools into LangChain BaseTool instances, ready to be bound
    to a LangGraph agent or ToolNode.

    Each tool invocation creates a fresh MCP session (stateless mode),
    which is the correct behaviour for independent place-search calls.

    Returns:
        List of LangChain-compatible tools (nearby_search, text_search, ...).

    Raises:
        Exception: If the MCP server is unreachable or returns an error.
    """
    client = get_google_maps_client()
    tools = await client.get_tools()

    logger.info(
        f"✅ Loaded {len(tools)} Google Maps tool(s) from MCP: "
        f"{[t.name for t in tools]}"
    )
    return tools


# =============================================================================
# CACHED TOOLS (optional helper for LangGraph graph construction)
# =============================================================================

async def get_google_map_tools_cached() -> List[BaseTool]:
    """
    Load Google Maps tools once and cache them for the process lifetime.

    Use this when you build your LangGraph graph at startup and want to
    avoid re-fetching the tool list on every agent invocation.

    Returns:
        Cached list of LangChain-compatible tools.
    """
    if not hasattr(get_google_map_tools_cached, "_cache"):
        get_google_map_tools_cached._cache = await get_google_map_tools()  # type: ignore[attr-defined]
    return get_google_map_tools_cached._cache  # type: ignore[attr-defined]


# =============================================================================
# MODULE TEST (run directly to verify tools load correctly)
# =============================================================================

async def _test():
    tools = await get_google_map_tools()
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description : {tool.description}")
        # args_schema can be a dict (Pydantic v2) or a class with .schema() (Pydantic v1)
        schema = tool.args_schema if isinstance(tool.args_schema, dict) else tool.args_schema.schema()
        print(f"  Input schema: {schema}")
        print()


if __name__ == "__main__":
    asyncio.run(_test())