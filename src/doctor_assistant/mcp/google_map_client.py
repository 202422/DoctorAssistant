"""
Google Maps MCP Client Module for Doctor Assistant Multi-Agent System.

Provides synchronous access to Google Maps services via Smithery MCP.
Used by the PharmacyFinder agent to locate nearby pharmacies.

Services available through this client:
- Geocoding (address → coordinates)
- Place search (find pharmacies, hospitals, etc.)
- Directions and distance calculations

Protocol: JSON-RPC 2.0 over HTTP with SSE (Server-Sent Events) responses
"""

import json
import time
import logging
import httpx
from typing import Optional

from ..utils import get_logger
from ..config import settings


logger = get_logger(__name__)


# =============================================================================
# GOOGLE MAPS MCP CLIENT
# =============================================================================

class GoogleMapsMCPClient:
    """
    Synchronous HTTP client for Google Maps via Smithery MCP.
    
    Used by PharmacyFinder agent to:
    - Search for nearby pharmacies
    - Get pharmacy details (address, hours, ratings)
    - Calculate distances from patient location
    """

    def __init__(self):
        """Initialize client with credentials from settings."""
        # Load MCP endpoint and API key from environment
        self.base_url = settings.MAP_SMITHERY_MCP_URL
        self.api_key = settings.MAP_SMITHERY_API_KEY

        # HTTP headers for MCP requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json, text/event-stream",  # SSE support
            "Content-Type": "application/json",
        }

        self.logger = logging.getLogger(__name__)

        # Persistent HTTP client with timeout configuration
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=15.0,  # Time to establish connection
                read=10.0,     # Time to receive response
                write=10.0,    # Time to send request
                pool=5.0,      # Time to acquire connection from pool
            ),
            limits=httpx.Limits(
                max_connections=10,         # Total concurrent connections
                max_keepalive_connections=5  # Reusable connections
            ),
        )

    def __del__(self):
        """Cleanup: close HTTP client when object is destroyed."""
        try:
            self._client.close()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # SSE RESPONSE PARSING
    # -------------------------------------------------------------------------

    def parse_sse_json(self, response_text: str):
        """
        Extract JSON data from Server-Sent Events (SSE) response.
        
        SSE format example:
            data: {"result": {...}}
        
        Args:
            response_text: Raw SSE response string.
        
        Returns:
            Parsed JSON object or raw text if parsing fails.
        """
        for line in response_text.splitlines():
            line = line.strip()
            # SSE data lines start with "data:"
            if line.startswith("data:"):
                json_part = line[len("data:"):].strip()
                try:
                    return json.loads(json_part)
                except json.JSONDecodeError:
                    return json_part
        return response_text

    # -------------------------------------------------------------------------
    # MCP TOOL INVOCATION
    # -------------------------------------------------------------------------

    def call_tool(self, tool_name: str, arguments: dict, max_retries: int = 2):
        """
        Call a Google Maps MCP tool with automatic retry on timeout.
        
        Available tools (examples):
        - "text_search": Find places by query
        - "geocode": Convert address to coordinates
        - "directions": Get route between points
        
        Args:
            tool_name: MCP tool to invoke (e.g., "text_search").
            arguments: Tool parameters as dictionary.
            max_retries: Retry attempts for timeout errors.
        
        Returns:
            Parsed response from MCP (usually dict or string).
        
        Raises:
            Exception: If all retries fail or MCP returns error.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"🔧 Calling Map MCP tool: {tool_name} (attempt {attempt + 1}/{max_retries})"
                )

                # Build JSON-RPC 2.0 request payload
                payload = {
                    "jsonrpc": "2.0",
                    "id": str(time.time()),  # Unique request ID
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                }

                # Send request to MCP server
                response = self._client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                )

                self.logger.debug(f"STATUS: {response.status_code}")
                self.logger.debug(f"RAW RESPONSE: {response.text[:1000]}")

                # Check for HTTP errors
                if response.status_code != 200:
                    raise Exception(f"MCP call failed: {response.status_code} - {response.text}")

                # Parse SSE response
                result = self.parse_sse_json(response.text)

                # Handle double-encoded JSON (string containing JSON)
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        pass

                # Return early if result is not a dict (simple response)
                if not isinstance(result, dict):
                    return result

                # Check for MCP-level errors
                if "error" in result:
                    raise Exception(result["error"])

                # Extract content from nested response structure
                # Structure: {"result": {"content": [{"type": "text", "text": "..."}]}}
                inner = result.get("result", {})
                content = inner.get("content", [])

                if content and isinstance(content[0], dict) and content[0].get("type") == "text":
                    text = content[0]["text"]
                    # Try to parse text content as JSON
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text

                return inner

            except httpx.ReadTimeout as e:
                # Retry on timeout
                last_error = e
                self.logger.warning(f"Timeout calling {tool_name}, retrying... ({attempt + 1})")
                continue

        # All retries exhausted
        raise last_error if last_error else Exception("Unknown error")


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_map_client: Optional[GoogleMapsMCPClient] = None


def get_google_maps_client() -> GoogleMapsMCPClient:
    """
    Get singleton Google Maps MCP client instance.
    
    Creates client on first call, reuses on subsequent calls.
    Used by PharmacyFinder agent to access Maps services.
    
    Returns:
        Shared GoogleMapsMCPClient instance.
    """
    global _map_client
    if _map_client is None:
        _map_client = GoogleMapsMCPClient()
    return _map_client


# =============================================================================
# MODULE TEST (run directly to verify connection)
# =============================================================================

if __name__ == "__main__":
    # Initialize client
    client = get_google_maps_client()

    # Display configuration
    print("Base URL:", client.base_url)
    print("API key set:", bool(client.api_key))

    # Test tool call
    try:
        res = client.call_tool("text_search", {"textQuery": "pharmacy near me"})
        print("Result:", res)

        # Unwrap nested result if present
        if isinstance(res, dict) and "result" in res:
            print("Unwrapped result:", res["result"])
    except Exception as exc:
        print("Tool call failed (expected if no config):", exc)