"""Main Graph - Connects Planner and Supervisor agents."""

from langgraph.graph import StateGraph, END
from langsmith import traceable

from .state.schemas import MainGraphState, PlanStep
from .config import get_llm
from .config.langsmith_config import setup_langsmith
from .prompts.planner_prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from .prompts.supervisor_prompts import SUPERVISOR_SYNTHESIS_PROMPT
from .agents.patient_data import run_patient_data_agent
from .agents.cardiovascular import run_cardiovascular_agent
from .agents.neurological import run_neurological_agent
from .utils import get_logger

import sys
import os
import re

SRC_DIR = os.path.abspath(os.path.dirname(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

logger = get_logger(__name__)

# Setup LangSmith on module import
LANGSMITH_ENABLED = setup_langsmith()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_plan_response(response: str) -> tuple[str, str, str, list[PlanStep]]:
    """Parse planner response to extract urgency, patient_name, reasoning, and plan."""
    
    # Extract urgency
    urgency = "medium"
    urgency_match = re.search(r"URGENCY:\s*(high|medium|low)", response, re.IGNORECASE)
    if urgency_match:
        urgency = urgency_match.group(1).lower()
    
    # Extract patient name
    patient_name = None
    name_match = re.search(r"PATIENT_NAME:\s*(.+?)(?=\n|REASONING:|$)", response, re.IGNORECASE)
    if name_match:
        extracted_name = name_match.group(1).strip()
        if extracted_name.lower() not in ["unknown", "not mentioned", "n/a", "none", ""]:
            patient_name = extracted_name
    
    # Extract reasoning
    reasoning = ""
    reasoning_match = re.search(r"REASONING:\s*(.+?)(?=PLAN:|$)", response, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()
    
    # Extract plan steps
    plan = []
    step_pattern = r"STEP\s*(\d+):\s*(\w+)\s*\|\s*(.+?)(?=\n|$)"
    matches = re.findall(step_pattern, response, re.IGNORECASE)
    
    for match in matches:
        step_num, agent, reason = match
        agent = agent.lower().strip()
        
        valid_agents = ["patient_data", "cardiovascular", "neurological", "pharmacy_finder"]
        if agent in valid_agents:
            plan.append(PlanStep(
                step=int(step_num),
                agent=agent,
                reason=reason.strip(),
                required=True
            ))
    
    return urgency, patient_name, reasoning, plan


def format_patient_info(patient_info: dict | None) -> str:
    """Format patient info for prompts."""
    if not patient_info:
        return "No patient information available."
    
    return f"""
- Name: {patient_info.get('name', 'N/A')}
- Age: {patient_info.get('age', 'N/A')}
- Gender: {patient_info.get('gender', 'N/A')}
- Medical History: {', '.join(patient_info.get('medical_history', [])) or 'None'}
- Medications: {', '.join(patient_info.get('current_medications', [])) or 'None'}
- Allergies: {', '.join(patient_info.get('allergies', [])) or 'None'}
"""


def format_diagnosis_results(results: list) -> str:
    """Format diagnosis results for synthesis."""
    if not results:
        return "No diagnosis results available."
    
    formatted = []
    for result in results:
        formatted.append(f"""
### {result.get('agent', 'Unknown').upper()} Agent:
- Conditions: {', '.join(result.get('possible_conditions', []))}
- Confidence: {result.get('confidence', 'N/A')}
- Recommendations: {', '.join(result.get('recommendations', [])[:3])}
- Warning Signs: {', '.join(result.get('warning_signs', [])[:3])}
""")
    return "\n".join(formatted)


# ============================================================
# NODE 1: PLANNER NODE
# ============================================================

@traceable(name="Planner Agent", tags=["planner", "planning"])
def planner_node(state: MainGraphState) -> MainGraphState:
    """
    Planner Agent: Analyzes query and creates execution plan.
    
    Reads: query
    Writes: plan, urgency, planner_reasoning, patient_name, current_step, next_agent
    """
    logger.info("=" * 60)
    logger.info("📋 PLANNER AGENT - Creating execution plan...")
    logger.info("=" * 60)
    
    llm = get_llm(temperature=0)
    
    prompt = PLANNER_SYSTEM_PROMPT + "\n\n" + PLANNER_USER_PROMPT.format(query=state["query"])
    
    response = llm.invoke(prompt)
    
    urgency, patient_name, reasoning, plan = parse_plan_response(response.content)
    
    # Ensure patient_data is first if patient name found
    if patient_name and (not plan or plan[0]["agent"] != "patient_data"):
        plan.insert(0, PlanStep(
            step=1,
            agent="patient_data",
            reason=f"Retrieve information for patient: {patient_name}",
            required=True
        ))
        for i, step in enumerate(plan):
            step["step"] = i + 1
    
    logger.info(f"⚡ Urgency: {urgency.upper()}")
    logger.info(f"👤 Patient Name: {patient_name or 'Not identified'}")
    logger.info(f"📝 Plan: {[s['agent'] for s in plan]}")
    logger.info(f"💭 Reasoning: {reasoning[:100]}...")
    
    return {
        **state,
        "plan": plan,
        "urgency": urgency,
        "planner_reasoning": reasoning,
        "patient_name": patient_name,
        "current_step": 0,
        "next_agent": None
    }


# ============================================================
# NODE 2: SUPERVISOR NODE (Router)
# ============================================================

@traceable(name="Supervisor Agent", tags=["supervisor", "routing"])
def supervisor_node(state: MainGraphState) -> MainGraphState:
    """
    Supervisor Agent: Decides which agent to call next based on plan.
    
    Reads: plan, current_step
    Writes: next_agent, thought
    """
    logger.info("-" * 40)
    logger.info("🧠 SUPERVISOR AGENT - Routing...")
    
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    
    # Check if plan is complete
    if current_step >= len(plan):
        logger.info("✅ All plan steps completed → SYNTHESIS")
        return {
            **state,
            "thought": "All plan steps completed. Ready to synthesize.",
            "next_agent": "synthesis"
        }
    
    # Get next agent from plan
    next_step = plan[current_step]
    next_agent = next_step["agent"]
    
    logger.info(f"📍 Step {current_step + 1}/{len(plan)}: {next_agent.upper()}")
    logger.info(f"   Reason: {next_step['reason']}")
    
    return {
        **state,
        "thought": f"Executing step {current_step + 1}: {next_agent}",
        "next_agent": next_agent
    }


# ============================================================
# NODE 3: PATIENT DATA NODE
# ============================================================

@traceable(name="Patient Data Agent", tags=["patient_data", "database", "mcp"])
def patient_data_node(state: MainGraphState) -> MainGraphState:
    """
    Patient Data Agent: Retrieves patient information by name.
    
    Reads: query, patient_name
    Writes: patient_info, current_step
    """
    logger.info("-" * 40)
    logger.info("👤 PATIENT DATA AGENT - Fetching patient...")
    
    patient_name = state.get("patient_name")
    
    if not patient_name:
        logger.warning("⚠️ No patient name provided.")
        return {
            **state,
            "patient_info": None,
            "current_step": state.get("current_step", 0) + 1
        }
    
    patient_info = run_patient_data_agent(
        query=state["query"],
        patient_name=patient_name
    )
    
    if patient_info:
        logger.info(f"✅ Found: {patient_info.get('name')} (Age: {patient_info.get('age')})")
    else:
        logger.warning(f"⚠️ Patient '{patient_name}' not found in database.")
    
    return {
        **state,
        "patient_info": patient_info,
        "current_step": state.get("current_step", 0) + 1
    }


# ============================================================
# NODE 4: CARDIOVASCULAR NODE
# ============================================================

@traceable(name="Cardiovascular Agent", tags=["cardiovascular", "diagnosis", "specialist"])
def cardiovascular_node(state: MainGraphState) -> MainGraphState:
    """
    Cardiovascular Agent: Runs cardiovascular diagnosis.
    
    Reads: query, patient_info
    Writes: diagnosis_results, current_step
    """
    logger.info("-" * 40)
    logger.info("🫀 CARDIOVASCULAR NODE - Analyzing...")
    
    diagnosis = run_cardiovascular_agent(
        query=state["query"],
        patient_info=state.get("patient_info") or {}
    )
    
    if diagnosis:
        logger.info(f"✅ Diagnosis complete. Confidence: {diagnosis.get('confidence')}")
        logger.info(f"   Conditions: {', '.join(diagnosis.get('possible_conditions', [])[:2])}")
    
    return {
        **state,
        "diagnosis_results": [diagnosis] if diagnosis else [],
        "current_step": state.get("current_step", 0) + 1
    }


# ============================================================
# NODE 5: NEUROLOGICAL NODE
# ============================================================

@traceable(name="Neurological Agent", tags=["neurological", "diagnosis", "specialist"])
def neurological_node(state: MainGraphState) -> MainGraphState:
    """
    Neurological Node: Runs neurological diagnosis.
    
    Reads: query, patient_info
    Writes: diagnosis_results, current_step
    """
    logger.info("-" * 40)
    logger.info("🧠 NEUROLOGICAL NODE - Analyzing...")
    
    diagnosis = run_neurological_agent(
        query=state["query"],
        patient_info=state.get("patient_info") or {}
    )
    
    if diagnosis:
        logger.info(f"✅ Diagnosis complete. Confidence: {diagnosis.get('confidence')}")
        logger.info(f"   Conditions: {', '.join(diagnosis.get('possible_conditions', [])[:2])}")
    
    return {
        **state,
        "diagnosis_results": [diagnosis] if diagnosis else [],
        "current_step": state.get("current_step", 0) + 1
    }


# ============================================================
# NODE 6: SYNTHESIS NODE
# ============================================================

@traceable(name="Synthesis Agent", tags=["synthesis", "final_response"])
def synthesis_node(state: MainGraphState) -> MainGraphState:
    """
    Synthesis Node: Combines all results into final response.
    
    Reads: query, patient_info, diagnosis_results, urgency
    Writes: final_response, is_complete
    """
    logger.info("-" * 40)
    logger.info("📝 SYNTHESIS NODE - Creating final response...")
    
    llm = get_llm(temperature=0.3)
    
    prompt = SUPERVISOR_SYNTHESIS_PROMPT.format(
        patient_info=format_patient_info(state.get("patient_info")),
        query=state["query"],
        diagnosis_results=format_diagnosis_results(state.get("diagnosis_results", []))
    )
    
    response = llm.invoke(prompt)
    
    # Add urgency warning if high
    final_response = response.content
    if state.get("urgency") == "high":
        final_response = "⚠️ **HIGH URGENCY** - Please seek immediate medical attention.\n\n" + final_response
    
    logger.info("✅ Synthesis complete!")
    
    return {
        **state,
        "final_response": final_response,
        "is_complete": True
    }


# ============================================================
# ROUTING FUNCTION
# ============================================================

def route_supervisor(state: MainGraphState) -> str:
    """Route to the appropriate node based on next_agent."""
    
    next_agent = state.get("next_agent", "synthesis")
    
    # Map plan agent names to graph node names
    routing_map = {
        "patient_data": "patient_data",
        "cardiovascular": "cardiovascular",
        "neurological": "neurological",
        "synthesis": "synthesis"
    }
    
    destination = routing_map.get(next_agent, "synthesis")
    logger.info(f"🔀 Routing to: {destination}")
    
    return destination


# ============================================================
# BUILD THE MAIN GRAPH
# ============================================================

def create_main_graph() -> StateGraph:
    """Create the main doctor assistant graph."""
    
    graph = StateGraph(MainGraphState)
    
    # Add all nodes (consistent naming!)
    graph.add_node("planner", planner_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("patient_data", patient_data_node)
    graph.add_node("cardiovascular", cardiovascular_node)
    graph.add_node("neurological", neurological_node)
    graph.add_node("synthesis", synthesis_node)
    
    # Set entry point
    graph.set_entry_point("planner")
    
    # Planner → Supervisor
    graph.add_edge("planner", "supervisor")
    
    # Supervisor routes to appropriate agent
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "patient_data": "patient_data",
            "cardiovascular": "cardiovascular",
            "neurological": "neurological",
            "synthesis": "synthesis"
        }
    )
    
    # All agent nodes return to Supervisor
    graph.add_edge("patient_data", "supervisor")
    graph.add_edge("cardiovascular", "supervisor")
    graph.add_edge("neurological", "supervisor")
    
    # Synthesis ends the graph
    graph.add_edge("synthesis", END)
    
    return graph.compile()


# ============================================================
# RUN FUNCTION
# ============================================================

@traceable(
    name="Doctor Assistant",
    tags=["main", "doctor-assistant"],
    metadata={"version": "1.0.0"}
)
def run_doctor_assistant(query: str) -> dict:
    """
    Run the complete Doctor Assistant pipeline.
    
    Args:
        query: User's medical query (should include patient name and symptoms)
        
    Returns:
        Dict with final_response and all collected data
    """
    
    initial_state: MainGraphState = {
        "query": query,
        "patient_name": None,
        "plan": [],
        "urgency": "medium",
        "planner_reasoning": "",
        "current_step": 0,
        "next_agent": None,
        "thought": "",
        "patient_info": None,
        "diagnosis_results": [],
        "final_response": "",
        "is_complete": False,
        "error": None
    }
    
    graph = create_main_graph()

    # Save graph visualization
    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        graph_path = os.path.join(SRC_DIR, "Whole_graph.png")
        
        with open(graph_path, "wb") as f:
            f.write(png_bytes)
        logger.info(f"📊 Graph saved to: {graph_path}")
    except Exception as e:
        logger.warning(f"⚠️ Could not save graph visualization: {e}")
    
    print("\n" + "=" * 70)
    print("🏥 DOCTOR ASSISTANT - STARTING")
    print("=" * 70)
    print(f"📋 Query: {query}")
    if LANGSMITH_ENABLED:
        print("📊 LangSmith tracing: ENABLED")
    print("=" * 70)
    
    final_state = graph.invoke(initial_state)
    
    print("\n" + "=" * 70)
    print("🏥 DOCTOR ASSISTANT - COMPLETE")
    print("=" * 70)
    
    return {
        "query": final_state["query"],
        "patient_name": final_state.get("patient_name"),
        "patient_info": final_state.get("patient_info"),
        "plan_executed": [s["agent"] for s in final_state.get("plan", [])],
        "urgency": final_state.get("urgency"),
        "diagnosis_results": final_state.get("diagnosis_results", []),
        "final_response": final_state.get("final_response", "")
    }


# ============================================================
# PRETTY PRINT
# ============================================================

def print_response(result: dict):
    """Pretty print the final response."""
    
    print("\n" + "=" * 70)
    print("🏥 DOCTOR ASSISTANT - FINAL RESPONSE")
    print("=" * 70)
    
    # Patient Info
    patient = result.get("patient_info")
    if patient:
        print(f"\n👤 Patient: {patient.get('name', 'Unknown')}")
        print(f"   Age: {patient.get('age', 'N/A')} | Gender: {patient.get('gender', 'N/A')}")
        print(f"   History: {', '.join(patient.get('medical_history', [])) or 'None'}")
        print(f"   Medications: {', '.join(patient.get('current_medications', [])) or 'None'}")
        print(f"   Allergies: {', '.join(patient.get('allergies', [])) or 'None'}")
    else:
        print(f"\n👤 Patient: {result.get('patient_name', 'Unknown')} (Not found in database)")
    
    # Execution Info
    print(f"\n⚡ Urgency: {result.get('urgency', 'N/A').upper()}")
    print(f"🔬 Agents Consulted: {' → '.join([a.upper() for a in result.get('plan_executed', [])])}")
    
    # Final Response
    print("\n" + "-" * 70)
    print("📋 ASSESSMENT:")
    print("-" * 70)
    print(result.get("final_response", "No response generated."))
    print("=" * 70)
    
    # LangSmith link
    if LANGSMITH_ENABLED:
        print("\n📊 View trace at: https://smith.langchain.com")


# ============================================================
# TEST / MAIN
# ============================================================

if __name__ == "__main__":
    
    # Test 1: Cardiovascular case
    print("\n" + "#" * 70)
    print("# TEST 1: Cardiovascular Case")
    print("#" * 70)
    
    result = run_doctor_assistant(
        "Youssef Kabbaj has been experiencing chest pain and shortness of breath for 2 days"
    )
    print_response(result)
    
    """
    # Test 2: Neurological case
    print("\n" + "#" * 70)
    print("# TEST 2: Neurological Case")
    print("#" * 70)
    
    result = run_doctor_assistant(
        "Jane Smith complains of severe headaches with visual disturbances and numbness in her left hand"
    )
    print_response(result)
    
    # Test 3: Mixed symptoms
    print("\n" + "#" * 70)
    print("# TEST 3: Mixed Symptoms (Both Specialists)")
    print("#" * 70)
    
    result = run_doctor_assistant(
        "Patient Youssef Kabbaj reports chest pain, dizziness, and confusion"
    )
    print_response(result)
    """