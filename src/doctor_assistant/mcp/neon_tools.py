"""LangChain tools wrapping the synchronous Neon MCP client."""

from src.doctor_assistant.mcp.neon_client import get_neon_client
from langchain_core.tools import Tool


# No asyncio, no nest_asyncio — client is fully sync now

def run_sql_tool(query: str) -> str:
    client = get_neon_client()
    result = client.run_sql(query)
    return str(result)


def list_tables_tool(_: str = "") -> str:
    client = get_neon_client()
    result = client.get_tables()
    return str(result)


def describe_table_tool(table_name: str) -> str:
    client = get_neon_client()
    result = client.describe_table(table_name)
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
            "Call this to discover what tables exist before writing any SQL query. "
            "Returns a list of table names."
        ),
    ),
    Tool(
        name="inspect_table_schema",
        func=describe_table_tool,
        description=(
            "Use this to understand the structure of a specific table (columns and types) "
            "when needed."
        ),
    ),
]