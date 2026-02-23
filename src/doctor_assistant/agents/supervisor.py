"""Supervisor Agent - Executes plan with 4 nodes."""

import re
from langgraph.graph import StateGraph, END

from ..config import get_llm
from ..state.schemas import (
    SupervisorState,
    PatientInfo,
    DiagnosisResult,
    PlanStep,
)
from ..prompts.supervisor_prompts import (
    SUPERVISOR_LLM_PROMPT,
    SUPERVISOR_SYNTHESIS_PROMPT,
)
from ..utils import get_logger

from .patient_data import run_patient_data_agent
from .cardiovascular import run_cardiovascular_agent
from .neurological import run_neurological_agent

logger = get_logger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_patient_info(patient_info: PatientInfo | None) -> str:
    """Format patient info for prompts."""
    if not patient_info:
        return "No patient information available yet."
    
    return f"""
- Name: {patient_info.get('name', 'N/A')}
- Age: {patient_info.get('age', 'N/A')}
- Gender: {patient_info.get('gender', 'N/A')}
- Medical History: {', '.join(patient_info.get('medical_history', [])) or 'None'}
- Medications: {', '.join(patient_info.get('current_medications', [])) or 'None'}
- Allergies: {', '.join(patient_info.get('allergies', [])) or 'None'}
"""


def format_plan(plan: list[PlanStep]) -> str:
    """Format plan for prompts."""
    if not plan:
        return "No plan available."
    
    lines = []
    for step in plan:
        lines.append(f"Step {step['step']}: {step['agent']} - {step['reason']}")
    return "\n".join(lines)


def format_diagnosis_results(results: list[DiagnosisResult]) -> str:
    """Format diagnosis results for prompts."""
    if not results:
        return "No diagnosis results yet."
    
    formatted = []
    for result in results:
        formatted.append(f"""
### {result.get('agent', 'Unknown').upper()} Agent:
- Conditions: {', '.join(result.get('possible_conditions', []))}
- Confidence: {result.get('confidence', 'N/A')}
- Recommendations: {', '.join(result.get('recommendations', [])[:3])}
""")
    return "\n".join(formatted)


# ============================================================
# NODE 1: LLM NODE (Router/Coordinator)
# ============================================================

def llm_node(state: SupervisorState) -> SupervisorState:
    """
    LLM Node: Decides which agent to call next based on plan and state.
    """
    logger.info("🧠 LLM Node - Deciding next action...")
    
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    
    # Check if plan is complete
    if current_step >= len(plan):
        logger.info("✅ Plan complete. Moving to synthesis.")
        return {
            **state,
            "thought": "All plan steps completed. Ready to synthesize final response.",
            "next_agent": "end",
            "should_continue": False
        }
    
    # Get next agent from plan
    next_step = plan[current_step]
    next_agent = next_step["agent"]
    
    logger.info(f"📍 Step {current_step + 1}/{len(plan)}: {next_agent.upper()}")
    logger.info(f"   Reason: {next_step['reason']}")
    
    return {
        **state,
        "thought": f"Executing step {current_step + 1}: {next_agent} - {next_step['reason']}",
        "next_agent": next_agent,
        "should_continue": True
    }


# ============================================================
# NODE 2: PATIENT DATA NODE
# ============================================================

def patient_data_node(state: SupervisorState) -> SupervisorState:
    """
    Patient Data Node: Retrieves patient information by name.
    """
    logger.info("👤 Patient Data Node - Fetching patient info...")
    
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
        logger.info(f"✅ Patient found: {patient_info.get('name')}")
    else:
        logger.warning(f"⚠️ No patient found with name: {patient_name}")
    
    return {
        **state,
        "patient_info": patient_info,
        "current_step": state.get("current_step", 0) + 1
    }


# ============================================================
# NODE 3: CARDIOVASCULAR NODE
# ============================================================

def cardiovascular_node(state: SupervisorState) -> SupervisorState:
    """
    Cardiovascular Node: Runs cardiovascular diagnosis.
    """
    logger.info("🫀 Cardiovascular Node - Running diagnosis...")
    
    diagnosis = run_cardiovascular_agent(
        query=state["query"],
        patient_info=state.get("patient_info") or {}
    )
    
    if diagnosis:
        logger.info(f"✅ Cardiovascular diagnosis complete. Confidence: {diagnosis.get('confidence')}")
    
    return {
        **state,
        "diagnosis_results": [diagnosis] if diagnosis else [],
        "current_step": state.get("current_step", 0) + 1
    }


# ============================================================
# NODE 4: NEUROLOGICAL NODE
# ============================================================

def neurological_node(state: SupervisorState) -> SupervisorState:
    """
    Neurological Node: Runs neurological diagnosis.
    """
    logger.info("🧠 Neurological Node - Running diagnosis...")
    
    diagnosis = run_neurological_agent(
        query=state["query"],
        patient_info=state.get("patient_info") or {}
    )
    
    if diagnosis:
        logger.info(f"✅ Neurological diagnosis complete. Confidence: {diagnosis.get('confidence')}")
    
    return {
        **state,
        "diagnosis_results": [diagnosis] if diagnosis else [],
        "current_step": state.get("current_step", 0) + 1
    }


# ============================================================
# NODE 5: SYNTHESIS NODE
# ============================================================

def synthesis_node(state: SupervisorState) -> SupervisorState:
    """
    Synthesis Node: Combines all results into final response.
    """
    logger.info("📝 Synthesis Node - Creating final response...")
    
    llm = get_llm(temperature=0.3)
    
    prompt = SUPERVISOR_SYNTHESIS_PROMPT.format(
        patient_info=format_patient_info(state.get("patient_info")),
        query=state["query"],
        diagnosis_results=format_diagnosis_results(state.get("diagnosis_results", []))
    )
    
    response = llm.invoke(prompt)
    
    logger.info("✅ Synthesis complete!")
    
    return {
        **state,
        "final_response": response.content,
        "is_complete": True
    }


# ============================================================
# ROUTING FUNCTION
# ============================================================

def route_to_agent(state: SupervisorState) -> str:
    """Route to the appropriate agent based on next_agent."""
    
    next_agent = state.get("next_agent", "end")
    
    if next_agent == "patient_data":
        return "patient_data_node"
    elif next_agent == "cardiovascular":
        return "cardiovascular_node"
    elif next_agent == "neurological":
        return "neurological_node"
    elif next_agent == "end":
        return "synthesis_node"
    else:
        logger.warning(f"⚠️ Unknown agent: {next_agent}. Ending.")
        return "synthesis_node"


# ============================================================
# BUILD THE GRAPH
# ============================================================

def create_supervisor_graph() -> StateGraph:
    """Create the supervisor agent graph with 4 agent nodes."""
    
    graph = StateGraph(SupervisorState)
    
    graph.add_node("llm_node", llm_node)
    graph.add_node("patient_data_agent", patient_data_node)
    graph.add_node("cardiovascular_agent", cardiovascular_node)
    graph.add_node("neurological_agent", neurological_node)
    graph.add_node("synthesis_node", synthesis_node)
    
    graph.set_entry_point("llm_node")
    
    graph.add_conditional_edges(
        "llm_node",
        route_to_agent,
        {
            "patient_data_agent": "patient_data_agent",
            "cardiovascular_agent": "cardiovascular_agent",
            "neurological_agent": "neurological_agent",
            "synthesis_node": "synthesis_node"
        }
    )
    
    graph.add_edge("patient_data_agent", "llm_node")
    graph.add_edge("cardiovascular_agent", "llm_node")
    graph.add_edge("neurological_agent", "llm_node")
    graph.add_edge("synthesis_node", END)
    
    return graph.compile()


# ============================================================
# RUN FUNCTION
# ============================================================

def run_supervisor_agent(
    query: str,
    patient_name: str = None,
    plan: list[PlanStep] = None,
    urgency: str = "medium"
) -> dict:
    """
    Run the supervisor agent with a given plan.
    
    Args:
        query: User's medical query
        patient_name: Patient name (extracted by planner)
        plan: Execution plan from Planner
        urgency: Urgency level from Planner
        
    Returns:
        Dict with final_response and all collected data
    """
    
    initial_state: SupervisorState = {
        "query": query,
        "patient_name": patient_name,
        "plan": plan or [],
        "urgency": urgency,
        "current_step": 0,
        "next_agent": None,
        "patient_info": None,
        "diagnosis_results": [],
        "thought": "",
        "should_continue": True,
        "final_response": "",
        "is_complete": False,
        "error": None
    }
    
    graph = create_supervisor_graph()
    
    logger.info("=" * 60)
    logger.info("🏥 SUPERVISOR AGENT STARTING")
    logger.info("=" * 60)
    logger.info(f"📋 Query: {query}")
    logger.info(f"👤 Patient Name: {patient_name or 'Not provided'}")
    logger.info(f"⚡ Urgency: {urgency}")
    logger.info(f"📝 Plan: {[s['agent'] for s in plan] if plan else 'No plan'}")
    logger.info("=" * 60)
    
    final_state = graph.invoke(initial_state)
    
    logger.info("=" * 60)
    logger.info("🏥 SUPERVISOR AGENT COMPLETE")
    logger.info("=" * 60)
    
    return {
        "query": final_state["query"],
        "patient_name": final_state.get("patient_name"),
        "patient_info": final_state.get("patient_info"),
        "diagnosis_results": final_state.get("diagnosis_results", []),
        "final_response": final_state.get("final_response", ""),
        "plan_executed": [s["agent"] for s in plan] if plan else []
    }


# ============================================================
# PRETTY PRINT
# ============================================================

def print_supervisor_response(result: dict):
    """Pretty print the supervisor response."""
    
    print("\n" + "=" * 70)
    print("🏥 DOCTOR ASSISTANT RESPONSE")
    print("=" * 70)
    
    patient = result.get("patient_info")
    if patient:
        print(f"\n👤 Patient: {patient.get('name', 'Unknown')} (Age: {patient.get('age', 'N/A')})")
    else:
        print(f"\n👤 Patient: {result.get('patient_name', 'Unknown')} (Not found in database)")
    
    plan = result.get("plan_executed", [])
    if plan:
        print(f"🔬 Agents Consulted: {' → '.join([a.upper() for a in plan])}")
    
    print("\n" + "-" * 70)
    print("📋 ASSESSMENT:")
    print("-" * 70)
    print(result.get("final_response", "No response generated."))
    print("=" * 70)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    from .planner import run_planner_agent, print_plan
    
    # Test: Full flow with patient name in query
    print("\n" + "=" * 70)
    print("TEST: Full Planner → Supervisor Flow (Patient Name in Query)")
    print("=" * 70)
    
    query = "John Doe has been experiencing chest pain and shortness of breath for 2 days"
    
    # Step 1: Run Planner
    print("\n📋 STEP 1: Running Planner...")
    plan_result = run_planner_agent(query=query)
    print_plan(plan_result)
    
    # Step 2: Run Supervisor with plan
    print("\n🏥 STEP 2: Running Supervisor...")
    result = run_supervisor_agent(
        query=query,
        patient_name=plan_result.get("patient_name"),
        plan=plan_result["plan"],
        urgency=plan_result["urgency"]
    )
    print_supervisor_response(result)