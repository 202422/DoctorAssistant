"""
Google Maps MCP Client Module for Doctor Assistant Multi-Agent System.

Provides async access to Google Maps services via Smithery MCP,
using the langchain-mcp-adapters library (MultiServerMCPClient).

The entire JSON-RPC 2.0 / Streamable HTTP transport layer is now handled
transparently by the MCP SDK — no manual HTTP wiring needed.

Services available through this client:
- Geocoding (address → coordinates)
- Place search (find pharmacies, hospitals, etc.)
- Directions and distance calculations
"""

import asyncio
from typing import Optional

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from ..utils import get_logger
from ..config import settings


logger = get_logger(__name__)


# =============================================================================
# HTTPX CLIENT FACTORY (SSL bypass for corporate proxy)
# =============================================================================

def no_ssl_verify_factory(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    """
    Factory that creates an httpx.AsyncClient with SSL verification disabled.

    Required because the corporate proxy re-signs HTTPS traffic with an
    internal CA certificate not trusted by Python's certifi bundle.

    Matches the McpHttpClientFactory protocol expected by the MCP session layer.
    """
    return httpx.AsyncClient(
        verify=False,
        headers=headers,
        timeout=timeout,
        auth=auth,
    )


# =============================================================================
# RETRY INTERCEPTOR
# =============================================================================

async def retry_interceptor(
    request: MCPToolCallRequest,
    handler,
    max_retries: int = 2,
    delay: float = 1.0,
):
    """
    Retry failed MCP tool calls with exponential backoff.

    Args:
        request:     The MCP tool call request.
        handler:     The next handler in the interceptor chain.
        max_retries: Number of retry attempts (default: 2).
        delay:       Base delay in seconds between retries (default: 1.0).
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            logger.info(
                f"🔧 Calling Map MCP tool: {request.name} "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            return await handler(request)

        except Exception as exc:
            last_error = exc
            wait_time = delay * (2 ** attempt)  # Exponential backoff
            logger.warning(
                f"Tool '{request.name}' failed (attempt {attempt + 1}): {exc}. "
                f"Retrying in {wait_time}s..."
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)

    raise last_error  # type: ignore[misc]


# =============================================================================
# GOOGLE MAPS MCP CLIENT FACTORY
# =============================================================================

def build_google_maps_mcp_client() -> MultiServerMCPClient:
    """
    Build a MultiServerMCPClient configured for the Google Maps Smithery MCP.

    Transport: streamable_http — Smithery Connect uses POST-based Streamable
               HTTP, NOT SSE (GET-based). Using 'sse' causes a 405 error.
    Auth:      Bearer token passed via the 'headers' field.
    Retry:     Handled by retry_interceptor.
    SSL:       no_ssl_verify_factory bypasses corporate proxy cert verification.

    Returns:
        A ready-to-use MultiServerMCPClient instance.
    """
    return MultiServerMCPClient(
        {
            "google_maps": {
                # ✅ Smithery Connect endpoint uses Streamable HTTP (POST),
                # NOT SSE (GET). 'sse' causes 405 Method Not Allowed.
                "transport": "streamable_http",
                "url": settings.MAP_SMITHERY_MCP_URL,
                "headers": {
                    "Authorization": f"Bearer {settings.MAP_SMITHERY_API_KEY}",
                },
                "httpx_client_factory": no_ssl_verify_factory,
            }
        },
        tool_interceptors=[retry_interceptor],
    )


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_map_client: Optional[MultiServerMCPClient] = None


def get_google_maps_client() -> MultiServerMCPClient:
    """
    Get the singleton MultiServerMCPClient for Google Maps.

    Creates the client on first call, reuses on subsequent calls.
    Used by google_map_tools.py to load LangChain-compatible tools.

    Returns:
        Shared MultiServerMCPClient instance.
    """
    global _map_client
    if _map_client is None:
        _map_client = build_google_maps_mcp_client()
    return _map_client


# =============================================================================
# MODULE TEST (run directly to verify connection)
# =============================================================================

async def _test():
    """Quick smoke-test: load tools and print their names."""
    client = get_google_maps_client()
    tools = await client.get_tools()
    print(f"✅ Connected. Available tools ({len(tools)}):")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:80]}")


if __name__ == "__main__":
    asyncio.run(_test())