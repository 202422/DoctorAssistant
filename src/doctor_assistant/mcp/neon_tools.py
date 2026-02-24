import asyncio
from src.doctor_assistant.mcp.neon_client import get_neon_client
from langchain_core.tools import Tool


# --------------------------------------------
# Helper to run async MCP calls inside sync tool
# --------------------------------------------

def _run_async(coro):
    return asyncio.run(coro)


# --------------------------------------------
# TOOL 1 — Execute SQL
# --------------------------------------------

def run_sql_tool(query: str) -> str:
    client = get_neon_client()
    result = _run_async(client.run_sql(query))
    return str(result)


# --------------------------------------------
# TOOL 2 — List Tables
# --------------------------------------------

def list_tables_tool(_: str = "") -> str:
    client = get_neon_client()
    result = _run_async(client.get_tables())
    return str(result)


# --------------------------------------------
# TOOL 3 — Describe Table Schema
# --------------------------------------------

def describe_table_tool(table_name: str) -> str:
    client = get_neon_client()
    result = _run_async(client.describe_table(table_name))
    return str(result)


neon_tools = [
    Tool(
    name="query_medical_database",
    func=run_sql_tool,
    description=(
        "Use this tool to execute READ-ONLY SQL queries to retrieve clinical data "
        "such as patients, diagnoses, medications, or allergies. "
        "Only SELECT statements are allowed."
    ),
),
Tool(
    name="list_database_tables",
    func=list_tables_tool,
    description=(
        "Call this to discover what tables exist before writing any SQL query."
        "when you need to understand the database structure. It returns a list of table names."
    ),
),
Tool(
    name="inspect_table_schema",
    func=describe_table_tool,
    description=(
        "Use this to understand the structure of a specifictable (columns and types) "
        "when needed"
    ),
),
]