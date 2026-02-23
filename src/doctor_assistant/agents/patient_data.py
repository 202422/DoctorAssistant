"""Patient Data Agent - Retrieves patient information using MCP client."""

import re
import asyncio
from langgraph.graph import StateGraph, END

from ..config import get_llm
from ..mcp.neon_client import (
    get_patient_by_id,
    search_patients,
    get_patient_medical_history,
    get_patient_medications,
    get_patient_allergies,
)
from ..state.schemas import PatientDataAgentState, PatientInfo, ReActStep
from ..prompts import PATIENT_DATA_THINK_PROMPT, PATIENT_DATA_EXTRACT_PROMPT
from ..utils import get_logger

logger = get_logger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_react_history(history: list[ReActStep]) -> str:
    """Format ReAct history for prompt."""
    if not history:
        return "No previous actions taken yet."
    
    formatted = []
    for i, step in enumerate(history, 1):
        formatted.append(f"""
--- Step {i} ---
Thought: {step['thought']}
Action: {step['action']}
Action Input: {step['action_input']}
Result: {step['observation'][:300]}...
""")
    return "\n".join(formatted)


def parse_llm_response(response: str) -> tuple[str, str, str]:
    """Parse LLM response to extract thought, action, and action_input."""
    
    thought = ""
    action = "search_by_name"
    action_input = ""
    
    thought_match = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|$)", response, re.DOTALL | re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()
    
    action_match = re.search(
        r"ACTION:\s*(search_by_id|search_by_name|get_history|get_medications|get_allergies|final_answer)", 
        response, 
        re.IGNORECASE
    )
    if action_match:
        action = action_match.group(1).lower()
    
    input_match = re.search(r"ACTION_INPUT:\s*(.+?)$", response, re.DOTALL | re.IGNORECASE)
    if input_match:
        action_input = input_match.group(1).strip()
    
    return thought, action, action_input


def format_patient_info(patient: PatientInfo) -> str:
    """Format patient info as readable string."""
    if not patient:
        return "No patient information found."
    
    lines = [
        f"Patient ID: {patient.get('patient_id', 'N/A')}",
        f"Name: {patient.get('name', 'N/A')}",
        f"Age: {patient.get('age', 'N/A')}",
        f"Gender: {patient.get('gender', 'N/A')}",
        f"Location: {patient.get('location', 'N/A')}",
        f"Medical History: {', '.join(patient.get('medical_history', [])) or 'None'}",
        f"Current Medications: {', '.join(patient.get('current_medications', [])) or 'None'}",
        f"Allergies: {', '.join(patient.get('allergies', [])) or 'None'}",
    ]
    
    return "\n".join(lines)


# ============================================================
# NODE 1: LLM NODE (Think & Decide)
# ============================================================

def llm_node(state: PatientDataAgentState) -> PatientDataAgentState:
    """
    LLM Node: Thinks about the query and decides next action.
    """
    logger.info(f"🧠 LLM Node - Iteration {state.get('iteration', 0) + 1}")
    
    llm = get_llm(temperature=0)
    
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 5)
    
    # Check if we already have complete patient info
    if state.get("patient_info") and iteration > 0:
        patient = state["patient_info"]
        if (patient.get("medical_history") and 
            patient.get("current_medications") and 
            patient.get("allergies") is not None):
            logger.info("✅ Patient data complete. Returning final answer.")
            return {
                **state,
                "thought": "Patient data is complete.",
                "action": "final_answer",
                "action_input": "complete",
                "is_complete": True
            }
    
    # Check if max iterations reached
    if iteration >= max_iterations:
        logger.info("⚠️ Max iterations reached.")
        return {
            **state,
            "thought": "Max iterations reached. Returning available data.",
            "action": "final_answer",
            "action_input": "complete",
            "is_complete": True
        }
    
    # First iteration with patient name - search by name
    if iteration == 0 and state.get("patient_name"):
        logger.info(f"🔍 First iteration - searching for patient: {state['patient_name']}")
        return {
            **state,
            "thought": f"Need to find patient by name: {state['patient_name']}",
            "action": "search_by_name",
            "action_input": state["patient_name"]
        }
    
    # Build prompt for subsequent iterations
    prompt = PATIENT_DATA_THINK_PROMPT.format(
        query=state.get("query", ""),
        patient_id=state.get("patient_id", "unknown"),
        patient_name=state.get("patient_name", "unknown"),
        react_history=format_react_history(state.get("react_history", [])),
        observation=state.get("observation", "No results yet.")
    )
    
    response = llm.invoke(prompt)
    thought, action, action_input = parse_llm_response(response.content)
    
    logger.info(f"💭 Thought: {thought[:100]}...")
    logger.info(f"⚡ Action: {action}")
    logger.info(f"📝 Action Input: {action_input}")
    
    if action == "final_answer":
        return {
            **state,
            "thought": thought,
            "action": action,
            "action_input": action_input,
            "is_complete": True
        }
    
    return {
        **state,
        "thought": thought,
        "action": action,
        "action_input": action_input
    }


# ============================================================
# NODE 2: DATABASE NODE (Execute Actions)
# ============================================================

def db_node(state: PatientDataAgentState) -> PatientDataAgentState:
    """
    Database Node: Executes database actions via MCP client.
    """
    action = state.get("action", "")
    action_input = state.get("action_input", "")
    
    logger.info(f"🔍 DB Node - Executing: {action}")
    
    observation = ""
    patient_info = state.get("patient_info") or {}
    
    try:
        if action == "search_by_id":
            try:
                patient_id = int(action_input)
                result = asyncio.run(get_patient_by_id(patient_id))
                
                if result:
                    patient_info = result
                    observation = f"Found patient: {format_patient_info(result)}"
                else:
                    observation = f"No patient found with ID: {patient_id}"
            except ValueError:
                observation = f"Invalid patient ID: {action_input}"
        
        elif action == "search_by_name":
            results = asyncio.run(search_patients(name=action_input))
            
            if results:
                if len(results) == 1:
                    patient_info = results[0]
                    observation = f"Found patient: {format_patient_info(results[0])}"
                else:
                    # Multiple matches - show list
                    patient_list = "\n".join([
                        f"  - ID: {p['patient_id']}, Name: {p['name']}, Age: {p['age']}"
                        for p in results
                    ])
                    observation = f"Found {len(results)} patients matching '{action_input}':\n{patient_list}\n\nUsing first match."
                    # Use first match
                    patient_info = results[0]
            else:
                observation = f"No patients found matching name: {action_input}"
        
        elif action == "get_history":
            try:
                patient_id = int(action_input) if action_input.isdigit() else int(patient_info.get("patient_id", 0))
                history = asyncio.run(get_patient_medical_history(patient_id))
                
                if history:
                    conditions = [h["condition"] for h in history]
                    patient_info["medical_history"] = conditions
                    history_str = "\n".join([
                        f"  - {h['condition']} (diagnosed: {h.get('diagnosis_date', 'N/A')})"
                        for h in history
                    ])
                    observation = f"Medical history:\n{history_str}"
                else:
                    patient_info["medical_history"] = []
                    observation = "No medical history found."
            except (ValueError, TypeError):
                observation = "Could not get medical history. Patient ID required."
        
        elif action == "get_medications":
            try:
                patient_id = int(action_input) if action_input.isdigit() else int(patient_info.get("patient_id", 0))
                medications = asyncio.run(get_patient_medications(patient_id))
                
                if medications:
                    med_list = [
                        f"{m['medication_name']} ({m.get('dosage', 'N/A')})"
                        for m in medications
                    ]
                    patient_info["current_medications"] = med_list
                    meds_str = "\n".join([f"  - {m}" for m in med_list])
                    observation = f"Current medications:\n{meds_str}"
                else:
                    patient_info["current_medications"] = []
                    observation = "No medications found."
            except (ValueError, TypeError):
                observation = "Could not get medications. Patient ID required."
        
        elif action == "get_allergies":
            try:
                patient_id = int(action_input) if action_input.isdigit() else int(patient_info.get("patient_id", 0))
                allergies = asyncio.run(get_patient_allergies(patient_id))
                
                if allergies:
                    allergy_list = [a["allergen"] for a in allergies]
                    patient_info["allergies"] = allergy_list
                    allergies_str = "\n".join([
                        f"  - {a['allergen']} (reaction: {a.get('reaction', 'N/A')})"
                        for a in allergies
                    ])
                    observation = f"Allergies:\n{allergies_str}"
                else:
                    patient_info["allergies"] = []
                    observation = "No allergies recorded."
            except (ValueError, TypeError):
                observation = "Could not get allergies. Patient ID required."
        
        else:
            observation = f"Unknown action: {action}"
    
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        observation = f"Error executing {action}: {str(e)}"
    
    logger.info(f"📚 Result: {observation[:200]}...")
    
    react_step = ReActStep(
        thought=state.get("thought", ""),
        action=action,
        action_input=action_input,
        observation=observation[:500]
    )
    
    new_iteration = state.get("iteration", 0) + 1
    
    return {
        **state,
        "observation": observation,
        "patient_info": patient_info if patient_info else None,
        "react_history": [react_step],
        "iteration": new_iteration
    }


# ============================================================
# ROUTING FUNCTION
# ============================================================

def should_continue(state: PatientDataAgentState) -> str:
    """Determine next node based on action."""
    
    if state.get("is_complete", False):
        logger.info("✅ Agent complete. Ending.")
        return END
    
    action = state.get("action", "")
    
    if action == "final_answer":
        logger.info("✅ Final answer ready. Ending.")
        return END
    
    if action in ["search_by_id", "search_by_name", "get_history", "get_medications", "get_allergies"]:
        logger.info(f"🔄 Continuing to DB node for: {action}")
        return "db_node"
    
    return END


# ============================================================
# BUILD THE GRAPH
# ============================================================

def create_patient_data_graph() -> StateGraph:
    """Create the patient data agent graph."""
    
    graph = StateGraph(PatientDataAgentState)
    
    graph.add_node("llm_node", llm_node)
    graph.add_node("db_node", db_node)
    
    graph.set_entry_point("llm_node")
    
    graph.add_conditional_edges(
        "llm_node",
        should_continue,
        {
            "db_node": "db_node",
            END: END
        }
    )
    
    graph.add_edge("db_node", "llm_node")
    
    return graph.compile()


# ============================================================
# RUN FUNCTION
# ============================================================

def run_patient_data_agent(
    query: str = "",
    patient_name: str = None,
    patient_id: int = None
) -> PatientInfo | None:
    """
    Run the patient data agent.
    
    Args:
        query: User query (optional context)
        patient_name: Patient name to search for
        patient_id: Direct patient ID if known
        
    Returns:
        PatientInfo dict or None if not found
    """
    
    initial_state: PatientDataAgentState = {
        "query": query,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "action": "",
        "action_input": "",
        "observation": "",
        "thought": "",
        "react_history": [],
        "iteration": 0,
        "max_iterations": 5,
        "patient_info": None,
        "is_complete": False,
        "error": None
    }
    
    graph = create_patient_data_graph()
    
    logger.info("👤 Starting Patient Data Agent...")
    if patient_name:
        logger.info(f"📛 Patient Name: {patient_name}")
    if patient_id:
        logger.info(f"🔢 Patient ID: {patient_id}")
    
    final_state = graph.invoke(initial_state)
    
    logger.info("👤 Patient Data Agent completed!")
    
    return final_state.get("patient_info")


# ============================================================
# PRETTY PRINT
# ============================================================

def print_patient_info(patient: PatientInfo):
    """Pretty print patient information."""
    
    if not patient:
        print("\n❌ No patient information found.")
        return
    
    print("\n" + "=" * 60)
    print("👤 PATIENT INFORMATION")
    print("=" * 60)
    print(f"ID:       {patient.get('patient_id', 'N/A')}")
    print(f"Name:     {patient.get('name', 'N/A')}")
    print(f"Age:      {patient.get('age', 'N/A')}")
    print(f"Gender:   {patient.get('gender', 'N/A')}")
    print(f"Location: {patient.get('location', 'N/A')}")
    
    print("\n" + "-" * 60)
    print("📋 MEDICAL HISTORY:")
    print("-" * 60)
    for condition in patient.get("medical_history", []):
        print(f"   • {condition}")
    if not patient.get("medical_history"):
        print("   No medical history recorded.")
    
    print("\n" + "-" * 60)
    print("💊 CURRENT MEDICATIONS:")
    print("-" * 60)
    for med in patient.get("current_medications", []):
        print(f"   • {med}")
    if not patient.get("current_medications"):
        print("   No medications recorded.")
    
    print("\n" + "-" * 60)
    print("⚠️  ALLERGIES:")
    print("-" * 60)
    for allergy in patient.get("allergies", []):
        print(f"   🚨 {allergy}")
    if not patient.get("allergies"):
        print("   No allergies recorded.")
    
    print("=" * 60)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    # Test 1: Search by name
    print("\n" + "=" * 60)
    print("TEST 1: Search by Patient Name")
    print("=" * 60)
    patient = run_patient_data_agent(patient_name="John Doe")
    print_patient_info(patient)
    
    # Test 2: Another patient
    print("\n" + "=" * 60)
    print("TEST 2: Search by Another Name")
    print("=" * 60)
    patient = run_patient_data_agent(patient_name="Jane Smith")
    print_patient_info(patient)
    
    # Test 3: Partial name
    print("\n" + "=" * 60)
    print("TEST 3: Partial Name Search")
    print("=" * 60)
    patient = run_patient_data_agent(patient_name="Youssef")
    print_patient_info(patient)