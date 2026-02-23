"""Prompts for Patient Data Agent."""

PATIENT_DATA_THINK_PROMPT = """You are a patient data retrieval assistant.
Your job is to find and retrieve patient information from the database.

## User Query:
{query}

## Known Information:
- Patient ID: {patient_id}
- Patient Name: {patient_name}

## Previous Actions:
{react_history}

## Last Result:
{observation}

---

## Available Actions:
1. **search_by_id** - Search for a patient by their ID number
2. **search_by_name** - Search for a patient by name (partial match supported)
3. **get_history** - Get detailed medical history for a patient (requires patient_id)
4. **get_medications** - Get current medications for a patient (requires patient_id)
5. **get_allergies** - Get allergies for a patient (requires patient_id)
6. **final_answer** - Return the complete patient information

## Your Task:
Analyze the query and decide what action to take next.

## Response Format (follow exactly):
THOUGHT: <your reasoning about what information you need>
ACTION: <one of: search_by_id, search_by_name, get_history, get_medications, get_allergies, final_answer>
ACTION_INPUT: <the input for the action - patient_id number, patient name, or "complete" for final_answer>
"""

PATIENT_DATA_EXTRACT_PROMPT = """Extract patient identification from the following query.

Query: {query}

Look for:
1. Patient ID (a number, often prefixed with "patient", "id", "#", or "P")
2. Patient name (a person's name)

## Response Format (follow exactly):
PATIENT_ID: <number or "unknown">
PATIENT_NAME: <name or "unknown">
"""