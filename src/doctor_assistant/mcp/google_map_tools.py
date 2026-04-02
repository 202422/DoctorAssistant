"""
Google Maps Tools Module for Doctor Assistant Multi-Agent System.

Provides LangChain-compatible tools for the PharmacyFinder agent by
loading them directly from the Google Maps MCP server via
langchain-mcp-adapters.

Tools are auto-discovered from the MCP server — no manual StructuredTool
definitions or Pydantic schemas needed. The MCP server itself advertises:
- nearby_search: Find places within a radius (lat/lng based)
- text_search:   Find places by text query (e.g., "pharmacies near X")

Usage (sync import — tools are loaded eagerly at import time):
    from doctor_assistant.mcp.google_map_tools import google_map_tools
    # Pass `google_map_tools` to your LangGraph agent / ToolNode
"""

import asyncio
import concurrent.futures
from typing import Any, List

from langchain_core.tools import StructuredTool

from .google_map_client import get_google_maps_client
from ..utils import get_logger


logger = get_logger(__name__)


# =============================================================================
# ASYNC → SYNC BRIDGE
# =============================================================================

def _run_async(coro) -> Any:
    """
    Run an async coroutine from a sync context safely.

    Handles two cases:
    - No running event loop: uses asyncio.run() directly.
    - Running event loop (LangGraph, FastAPI): runs in a separate thread
      with its own event loop to avoid 'cannot run nested event loop' error.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Running loop exists — run in a separate thread with its own loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


# =============================================================================
# TOOL WRAPPER
# =============================================================================

def _wrap_as_structured_tool(mcp_tool) -> StructuredTool:
    """
    Wrap an async-only MCP tool into a StructuredTool with sync support.

    MCP tools from langchain-mcp-adapters only implement _arun() (async).
    LangGraph may call tools synchronously, which raises:
    'StructuredTool does not support sync invocation.'

    This wrapper adds a sync _run() that bridges to the async _arun()
    via a dedicated thread pool, making the tool safe for both sync
    and async invocation contexts.

    Args:
        mcp_tool: The async-only BaseTool returned by client.get_tools().

    Returns:
        A StructuredTool instance with both sync and async support.
    """
    async def _arun(**kwargs) -> Any:
        return await mcp_tool.arun(kwargs)

    def _run(**kwargs) -> Any:
        return _run_async(mcp_tool.arun(kwargs))

    return StructuredTool(
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=mcp_tool.args_schema,
        func=_run,
        coroutine=_arun,
    )


# =============================================================================
# TOOL LOADER
# =============================================================================

async def get_google_map_tools() -> List[StructuredTool]:
    """
    Load Google Maps tools from the MCP server and wrap them as StructuredTools.

    Connects to the Smithery MCP endpoint, converts all exposed MCP tools
    into StructuredTool instances with both sync and async support.

    Returns:
        List of StructuredTool instances (nearby_search, text_search, ...).

    Raises:
        Exception: If the MCP server is unreachable or returns an error.
    """
    client = get_google_maps_client()
    raw_tools = await client.get_tools()

    tools = [_wrap_as_structured_tool(t) for t in raw_tools]

    logger.info(
        f"✅ Loaded {len(tools)} Google Maps tool(s) from MCP: "
        f"{[t.name for t in tools]}"
    )
    return tools


# =============================================================================
# CACHED TOOLS (optional helper for LangGraph graph construction)
# =============================================================================

async def get_google_map_tools_cached() -> List[StructuredTool]:
    """
    Load Google Maps tools once and cache them for the process lifetime.

    Returns:
        Cached list of StructuredTool instances.
    """
    if not hasattr(get_google_map_tools_cached, "_cache"):
        get_google_map_tools_cached._cache = await get_google_map_tools()  # type: ignore[attr-defined]
    return get_google_map_tools_cached._cache  # type: ignore[attr-defined]


# =============================================================================
# MODULE-LEVEL TOOL LIST (sync-importable)
# =============================================================================

def _load_tools_sync() -> List[StructuredTool]:
    """
    Eagerly load Google Maps tools at import time using a sync wrapper.

    Returns:
        List of StructuredTool instances.
    """
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            return loop.run_until_complete(get_google_map_tools())

        # Loop already running (e.g. Jupyter, FastAPI startup)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, get_google_map_tools())
            return future.result()

    except Exception as exc:
        logger.error(f"❌ Failed to load Google Maps tools at import time: {exc}")
        raise


# Sync-importable list of all Google Maps MCP tools as StructuredTool instances.
# Loaded once when this module is first imported.
#
# Usage:
#   from doctor_assistant.mcp.google_map_tools import google_map_tools
#   tool_node = ToolNode(google_map_tools)
#   model_with_tools = model.bind_tools(google_map_tools)
google_map_tools: List[StructuredTool] = _load_tools_sync()


# =============================================================================
# MODULE TEST (run directly to verify tools load correctly)
# =============================================================================

async def _test():
    for tool in google_map_tools:
        print(f"Tool : {tool.name}")
        print(f"  Type        : {type(tool).__name__}")
        print(f"  Description : {tool.description}")
        schema = tool.args_schema if isinstance(tool.args_schema, dict) else tool.args_schema.model_json_schema()
        print(f"  Input schema: {schema}")
        print()


if __name__ == "__main__":
    asyncio.run(_test())