"""
Neon Database Tools Module for Doctor Assistant Multi-Agent System.

Provides LangChain-compatible tools for the PatientDataRetriever agent
to query patient medical records stored in Neon PostgreSQL database.

Tools:
- query_medical_database: Execute SELECT queries on patient data
- list_database_tables: Discover available tables
- inspect_table_schema: Get column details for a table

Note: All operations are READ-ONLY for patient data safety.
"""

from langchain_core.tools import Tool

from src.doctor_assistant.mcp.neon_client import get_neon_client


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def run_sql_tool(query: str) -> str:
    """
    Execute a SQL query against the medical database.
    
    Used by PatientDataRetriever agent to fetch:
    - Patient demographics
    - Medical history
    - Current medications
    - Allergies and conditions
    
    Args:
        query: SQL SELECT statement.
    
    Returns:
        Query results as string.
    """
    client = get_neon_client()
    result = client.run_sql(query)
    return str(result)


def list_tables_tool(_: str = "") -> str:
    """
    List all tables in the medical database.
    
    Called by agent to discover schema before writing queries.
    Typical tables: patients, diagnoses, medications, allergies.
    
    Args:
        _: Unused (required by LangChain Tool interface).
    
    Returns:
        List of table names as string.
    """
    client = get_neon_client()
    result = client.get_tables()
    return str(result)


def describe_table_tool(table_name: str) -> str:
    """
    Get column names and types for a specific table.
    
    Helps agent understand table structure before querying.
    
    Args:
        table_name: Name of table to describe.
    
    Returns:
        Column definitions as string.
    """
    client = get_neon_client()
    result = client.describe_table(table_name)
    return str(result)


# =============================================================================
# TOOL DEFINITIONS (exported for agent binding)
# =============================================================================

neon_tools = [
    # -------------------------------------------------------------------------
    # SQL QUERY TOOL
    # -------------------------------------------------------------------------
    Tool(
        name="query_medical_database",
        func=run_sql_tool,
        description=(
            "Execute READ-ONLY SQL queries to retrieve patient clinical data. "
            "Use for: patients, diagnoses, medications, allergies. "
            "Only SELECT statements allowed."
        ),
    ),

    # -------------------------------------------------------------------------
    # TABLE DISCOVERY TOOL
    # -------------------------------------------------------------------------
    Tool(
        name="list_database_tables",
        func=list_tables_tool,
        description=(
            "Discover available tables before writing SQL queries. "
            "Call this FIRST to know what data is available. "
            "Returns list of table names."
        ),
    ),

    # -------------------------------------------------------------------------
    # SCHEMA INSPECTION TOOL
    # -------------------------------------------------------------------------
    Tool(
        name="inspect_table_schema",
        func=describe_table_tool,
        description=(
            "Get column names and data types for a specific table. "
            "Use to understand table structure before querying. "
            "Input: table name (e.g., 'patients')."
        ),
    ),
]