"""Neon PostgreSQL MCP Client via Smithery for patient data retrieval."""

import json
import asyncio
import httpx
import logging
from typing import Optional, Any, List

from ..state.schemas import PatientInfo
from ..utils import get_logger
from ..config import settings

logger = get_logger(__name__)


# ============================================================
# SMITHERY MCP CLIENT
# ============================================================

class NeonMCPClient:
    """Client for Neon PostgreSQL via Smithery MCP."""

    def __init__(self):
        """Initialize Smithery MCP Client."""
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

    # -----------------------------
    # SSE PARSING
    # -----------------------------
    async def parse_sse_json(self, response_text: str):  # FIX 1: added `self`
        """
        Extract JSON from SSE-style MCP response.
        """
        for line in response_text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                json_part = line[len("data:"):].strip()
                try:
                    return json.loads(json_part)
                except json.JSONDecodeError:
                    return json_part  # fallback to raw text
        # fallback if no data line found
        return response_text

    # -----------------------------
    # MCP TOOL CALL
    # -----------------------------
    async def call_tool(self, tool_name: str, arguments: dict):
        self.logger.info(f"🔧 Calling MCP tool: {tool_name}")

        payload = {
            "jsonrpc": "2.0",
            "id": str(asyncio.get_running_loop().time()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )

            self.logger.debug(f"STATUS: {response.status_code}")
            self.logger.debug(f"RAW RESPONSE: {response.text[:1000]}")

            if response.status_code != 200:
                raise Exception(f"MCP call failed: {response.status_code} - {response.text}")

            result = await self.parse_sse_json(response.text)  # FIX 2: use self.parse_sse_json

            if isinstance(result, dict) and "error" in result:
                raise Exception(result["error"])

            # FIX 3: Unwrap nested SSE content structure:
            # result -> result -> content -> [0] -> text (JSON string of actual data)
            inner = result.get("result", {})
            content = inner.get("content", [])
            if content and isinstance(content[0], dict) and content[0].get("type") == "text":
                text = content[0]["text"]
                try:
                    return json.loads(text)  # parse the actual SQL result
                except json.JSONDecodeError:
                    return text
            return inner

    # -----------------------------
    # LIST TOOLS
    # -----------------------------
    async def list_tools(self) -> List[dict]:
        """List all available MCP tools."""
        self.logger.info("📋 Listing available MCP tools...")

        payload = {
            "jsonrpc": "2.0",
            "id": str(asyncio.get_running_loop().time()),
            "method": "tools/list",
            "params": {},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )

            self.logger.debug(f"STATUS: {response.status_code}")
            self.logger.debug(f"RAW RESPONSE: {response.text[:500]}")

            if response.status_code != 200:
                self.logger.error(f"❌ Failed to list tools: {response.status_code}")
                return []

            try:
                result = await self.parse_sse_json(response.text)  # FIX 4: use SSE parser, not response.json()
            except Exception:
                self.logger.error("❌ Failed to parse SSE response")
                return []

            tools = result.get("result", {}).get("tools", [])
            self.logger.info(f"✅ Found {len(tools)} tools")
            return tools

    # ============================================================
    # SQL EXECUTION
    # ============================================================

    async def run_sql(self, query: str) -> list[dict]:
        """
        Execute a SQL query.

        Args:
            query: SQL query string

        Returns:
            Query results as list of dicts
        """
        logger.info(f"🔍 Executing SQL: {query[:100]}...")

        arguments = {
            "sql": query,
            "projectId": self.project_id,
            "databaseName": self.database_name
        }

        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = await self.call_tool("run_sql", arguments)

        logger.info(f"✅ Query executed successfully")
        return result if isinstance(result, list) else []

    async def run_sql_transaction(self, queries: list[str]) -> list[dict]:
        """
        Execute multiple SQL queries in a transaction.

        Args:
            queries: List of SQL query strings

        Returns:
            Transaction results
        """
        logger.info(f"🔄 Executing transaction with {len(queries)} queries...")

        arguments = {
            "sqlStatements": queries,
            "projectId": self.project_id,
            "databaseName": self.database_name
        }

        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = await self.call_tool("run_sql_transaction", arguments)

        logger.info(f"✅ Transaction completed successfully")
        return result

    # ============================================================
    # DATABASE INTROSPECTION
    # ============================================================

    async def get_tables(self) -> list[str]:
        """Get all tables in the database."""
        logger.info("📋 Fetching database tables...")

        arguments = {
            "projectId": self.project_id,
            "databaseName": self.database_name
        }

        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = await self.call_tool("get_database_tables", arguments)

        return result

    async def describe_table(self, table_name: str) -> dict:
        """Get schema of a specific table."""
        logger.info(f"📋 Describing table: {table_name}")

        arguments = {
            "tableName": table_name,
            "projectId": self.project_id,
            "databaseName": self.database_name
        }

        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = await self.call_tool("describe_table_schema", arguments)

        return result

    async def get_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        logger.info("🔌 Getting connection string...")

        arguments = {
            "projectId": self.project_id,
            "databaseName": self.database_name
        }

        if self.branch_id:
            arguments["branchId"] = self.branch_id

        result = await self.call_tool("get_connection_string", arguments)

        return result


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


# ============================================================
# PATIENT DATA OPERATIONS
# ============================================================

async def get_patient_by_id(patient_id: int) -> Optional[PatientInfo]:
    """
    Retrieve patient information by ID.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        PatientInfo dict or None if not found
    """
    logger.info(f"🔍 Fetching patient data for ID: {patient_id}")

    client = get_neon_client()

    # Get patient basic info
    patient_query = f"""
        SELECT patient_id, name, age, gender, location
        FROM patients
        WHERE patient_id = {patient_id}
    """

    patient_result = await client.run_sql(patient_query)

    if not patient_result or len(patient_result) == 0:
        logger.warning(f"⚠️ Patient not found: {patient_id}")
        return None

    patient_row = patient_result[0]

    # Get medical history
    history_query = f"""
        SELECT condition
        FROM medical_history
        WHERE patient_id = {patient_id}
    """
    history_result = await client.run_sql(history_query)
    medical_history = [r["condition"] for r in history_result] if history_result else []

    # Get medications
    meds_query = f"""
        SELECT medication_name, dosage
        FROM medications
        WHERE patient_id = {patient_id}
    """
    meds_result = await client.run_sql(meds_query)
    medications = [
        f"{r['medication_name']} ({r['dosage']})" if r.get('dosage') else r['medication_name']
        for r in meds_result
    ] if meds_result else []

    # Get allergies
    allergies_query = f"""
        SELECT allergen
        FROM allergies
        WHERE patient_id = {patient_id}
    """
    allergies_result = await client.run_sql(allergies_query)
    allergies = [r["allergen"] for r in allergies_result] if allergies_result else []

    patient = PatientInfo(
        patient_id=str(patient_row["patient_id"]),
        name=patient_row["name"],
        age=patient_row["age"],
        gender=patient_row["gender"],
        medical_history=medical_history,
        current_medications=medications,
        allergies=allergies,
        location=patient_row["location"]
    )

    logger.info(f"✅ Patient found: {patient['name']}")
    return patient


async def search_patients(
    name: str = None,
    age_min: int = None,
    age_max: int = None
) -> list[PatientInfo]:
    """
    Search patients by criteria.

    Args:
        name: Partial name match (case-insensitive)
        age_min: Minimum age
        age_max: Maximum age

    Returns:
        List of matching PatientInfo dicts
    """
    logger.info(f"🔍 Searching patients: name={name}, age={age_min}-{age_max}")

    client = get_neon_client()

    conditions = []

    if name:
        conditions.append(f"LOWER(name) LIKE LOWER('%{name}%')")

    if age_min is not None:
        conditions.append(f"age >= {age_min}")

    if age_max is not None:
        conditions.append(f"age <= {age_max}")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = f"""
        SELECT patient_id
        FROM patients
        WHERE {where_clause}
        ORDER BY name
        LIMIT 50
    """

    result = await client.run_sql(query)

    if not result:
        return []

    # Fetch full patient info for each match
    patients = []
    for row in result:
        patient = await get_patient_by_id(row["patient_id"])
        if patient:
            patients.append(patient)

    logger.info(f"✅ Found {len(patients)} patients")
    return patients


async def get_patient_medical_history(patient_id: int) -> list[dict]:
    """
    Get detailed medical history for a patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        List of medical history records
    """
    logger.info(f"🔍 Fetching medical history for patient: {patient_id}")

    client = get_neon_client()

    query = f"""
        SELECT
            history_id,
            patient_id,
            condition,
            diagnosis_date,
            notes
        FROM medical_history
        WHERE patient_id = {patient_id}
        ORDER BY diagnosis_date DESC
    """

    result = await client.run_sql(query)

    logger.info(f"✅ Found {len(result) if result else 0} medical records")
    return result or []


async def get_patient_medications(patient_id: int) -> list[dict]:
    """
    Get current medications for a patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        List of medication records
    """
    logger.info(f"🔍 Fetching medications for patient: {patient_id}")

    client = get_neon_client()

    query = f"""
        SELECT
            medication_id,
            patient_id,
            medication_name,
            dosage,
            start_date
        FROM medications
        WHERE patient_id = {patient_id}
        ORDER BY start_date DESC
    """

    result = await client.run_sql(query)

    logger.info(f"✅ Found {len(result) if result else 0} medications")
    return result or []


async def get_patient_allergies(patient_id: int) -> list[dict]:
    """
    Get allergies for a patient.

    Args:
        patient_id: The patient's unique identifier

    Returns:
        List of allergy records
    """
    logger.info(f"🔍 Fetching allergies for patient: {patient_id}")

    client = get_neon_client()

    query = f"""
        SELECT
            allergy_id,
            patient_id,
            allergen,
            reaction
        FROM allergies
        WHERE patient_id = {patient_id}
    """

    result = await client.run_sql(query)

    logger.info(f"✅ Found {len(result) if result else 0} allergies")
    return result or []


# ============================================================
# SYNC WRAPPERS (for non-async contexts)
# ============================================================

def get_patient_by_id_sync(patient_id: int) -> Optional[PatientInfo]:
    """Synchronous wrapper for get_patient_by_id."""
    return asyncio.run(get_patient_by_id(patient_id))


def search_patients_sync(
    name: str = None,
    age_min: int = None,
    age_max: int = None
) -> list[PatientInfo]:
    """Synchronous wrapper for search_patients."""
    return asyncio.run(search_patients(name, age_min, age_max))


def get_patient_medical_history_sync(patient_id: int) -> list[dict]:
    """Synchronous wrapper for get_patient_medical_history."""
    return asyncio.run(get_patient_medical_history(patient_id))


def get_patient_medications_sync(patient_id: int) -> list[dict]:
    """Synchronous wrapper for get_patient_medications."""
    return asyncio.run(get_patient_medications(patient_id))


def get_patient_allergies_sync(patient_id: int) -> list[dict]:
    """Synchronous wrapper for get_patient_allergies."""
    return asyncio.run(get_patient_allergies(patient_id))


# ============================================================
# PRETTY PRINT
# ============================================================

def print_patient(patient: PatientInfo):
    """Pretty print patient information."""
    print("\n" + "=" * 50)
    print("📋 PATIENT DATA")
    print("=" * 50)
    print(f"ID:          {patient['patient_id']}")
    print(f"Name:        {patient['name']}")
    print(f"Age:         {patient['age']}")
    print(f"Gender:      {patient['gender']}")
    print(f"Location:    {patient['location']}")
    print("-" * 50)
    print("Medical History:")
    for condition in patient['medical_history']:
        print(f"   • {condition}")
    print("-" * 50)
    print("Current Medications:")
    for med in patient['current_medications']:
        print(f"   💊 {med}")
    print("-" * 50)
    print("Allergies:")
    for allergy in patient['allergies']:
        print(f"   ⚠️ {allergy}")
    print("=" * 50)


# ============================================================
# TEST
# ============================================================

async def test_connection():
    """Test the Smithery MCP connection."""
    logger.info("🧪 Testing Smithery MCP connection...")

    try:
        client = get_neon_client()

        # List available tools
        tools = await client.list_tools()
        print(f"\n📋 Available MCP Tools ({len(tools)}):")
        for tool in tools[:10]:  # Show first 10
            print(f"   • {tool.get('name', 'unknown')}")

        # Test simple query
        result = await client.run_sql("SELECT 1 as test")

        if result and len(result) > 0:
            logger.info("✅ Smithery MCP connection successful!")
            return True

    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        # Test connection
        connected = await test_connection()
        if not connected:
            print("❌ Could not connect to Neon via Smithery")
            return

        # Uncomment to setup database (run once)
        # await setup_database()
        # await seed_sample_data()

        # Test fetching a patient
        print("\n🧪 Testing patient retrieval...\n")

        patient = await get_patient_by_id(1)
        if patient:
            print_patient(patient)
        else:
            print("No patient found with ID 1")
            print("Run setup_database() and seed_sample_data() first!")

        # Search patients
        print("\n🔍 Searching for patients over 50...")
        patients = await search_patients(age_min=50)
        for p in patients:
            print(f"   Found: {p['name']} (Age: {p['age']})")

    asyncio.run(main())