"""Neon PostgreSQL MCP Client via Smithery — fully synchronous implementation."""

import json
import time
import logging
import httpx
from typing import Optional, List

from ..utils import get_logger
from ..config import settings

logger = get_logger(__name__)


# ============================================================
# SMITHERY MCP CLIENT (sync)
# ============================================================

class NeonMCPClient:
    """Synchronous client for Neon PostgreSQL via Smithery MCP."""

    def __init__(self):
        self.base_url = settings.SMITHERY_MCP_URL
        self.api_key = settings.SMITHERY_API_KEY
        self.project_id = settings.NEON_PROJECT_ID
        self.branch_id = getattr(settings, "NEON_BRANCH_ID", None)
        self.database_name = getattr(settings, "NEON_DATABASE_NAME", "neondb")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

        self.logger = logging.getLogger(__name__)

        # Persistent synchronous HTTP client — no async, no event loop conflicts
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=15.0,
                read=60.0,
                write=30.0,   # was 10s — too short for parallel SQL payloads
                pool=15.0
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
        """Extract JSON from SSE-style MCP response."""
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
    # MCP TOOL CALL (sync)
    # -----------------------------

    def call_tool(self, tool_name: str, arguments: dict):
        self.logger.info(f"🔧 Calling MCP tool: {tool_name}")

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

        if isinstance(result, dict) and "error" in result:
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

    # -----------------------------
    # LIST TOOLS (sync)
    # -----------------------------

    def list_tools(self) -> List[dict]:
        self.logger.info("📋 Listing available MCP tools...")

        payload = {
            "jsonrpc": "2.0",
            "id": str(time.time()),
            "method": "tools/list",
            "params": {},
        }

        response = self._client.post(
            self.base_url,
            headers=self.headers,
            json=payload
        )

        if response.status_code != 200:
            self.logger.error(f"❌ Failed to list tools: {response.status_code}")
            return []

        try:
            result = self.parse_sse_json(response.text)
        except Exception:
            self.logger.error("❌ Failed to parse SSE response")
            return []

        tools = result.get("result", {}).get("tools", [])
        self.logger.info(f"✅ Found {len(tools)} tools")
        return tools

    # ============================================================
    # SQL EXECUTION (sync)
    # ============================================================

    def run_sql(self, query: str) -> list[dict]:
        logger.info(f"🔍 Executing SQL: {query[:100]}...")

        arguments = {
            "sql": query,
            "projectId": self.project_id,
            "databaseName": self.database_name
        }
        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = self.call_tool("run_sql", arguments)
        logger.info("✅ Query executed successfully")
        return result if isinstance(result, list) else []

    def run_sql_transaction(self, queries: list[str]) -> list[dict]:
        logger.info(f"🔄 Executing transaction with {len(queries)} queries...")

        arguments = {
            "sqlStatements": queries,
            "projectId": self.project_id,
            "databaseName": self.database_name
        }
        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = self.call_tool("run_sql_transaction", arguments)
        logger.info("✅ Transaction completed successfully")
        return result

    # ============================================================
    # DATABASE INTROSPECTION (sync)
    # ============================================================

    def get_tables(self) -> list[str]:
        logger.info("📋 Fetching database tables...")
        arguments = {"projectId": self.project_id, "databaseName": self.database_name}
        if self.branch_id:
            arguments["branchId"] = self.branch_id
        return self.call_tool("get_database_tables", arguments)

    def describe_table(self, table_name: str) -> dict:
        logger.info(f"📋 Describing table: {table_name}")
        arguments = {
            "tableName": table_name,
            "projectId": self.project_id,
            "databaseName": self.database_name
        }
        if self.branch_id:
            arguments["branchId"] = self.branch_id
        return self.call_tool("describe_table_schema", arguments)

    def get_connection_string(self) -> str:
        logger.info("🔌 Getting connection string...")
        arguments = {"projectId": self.project_id, "databaseName": self.database_name}
        if self.branch_id:
            arguments["branchId"] = self.branch_id
        return self.call_tool("get_connection_string", arguments)


# ============================================================
# GLOBAL CLIENT INSTANCE
# ============================================================

_client: Optional[NeonMCPClient] = None


def get_neon_client() -> NeonMCPClient:
    """Get or create global Neon MCP client."""
    global _client
    if _client is None:
        _client = NeonMCPClient()
    return _client