"""
Graph Module - Main Multi-Agent Medical Workflow for Doctor Assistant.

Defines the LangGraph state machine that orchestrates the Planner-Supervisor
architecture with specialist agents.

Flow:
    START → Planner → Supervisor ⇄ [Specialists] → Synthesis → END

Specialists:
    - patient_data_agent: Fetches patient records from Neon DB
    - cardiovascular_agent: RAG-based heart condition diagnosis
    - neurological_agent: RAG-based neurological diagnosis
    - pharmacy_finder_agent: Locates nearby pharmacies via Google Maps
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import State

# Initialize LangSmith tracing before any graph operations
from .config import setup_langsmith
_LANGSMITH_ENABLED = setup_langsmith()

# Import all agent functions
from .agents import (
    planner_agent,
    run_pharmacy_finder_agent,
    supervisor_agent,
    run_patient_data_agent,
    run_cardiovascular_agent,
    run_neurological_agent,
    synthesis_agent,
)

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

builder = StateGraph(State)

# -----------------------------------------------------------------------------
# NODE REGISTRATION
# -----------------------------------------------------------------------------
# Each node corresponds to an agent in the multi-agent system

builder.add_node("planner_agent",       planner_agent)          # Creates execution plan
builder.add_node("supervisor_agent",    supervisor_agent)       # Routes to specialists
builder.add_node("patient_data_agent",  run_patient_data_agent) # Queries Neon DB
builder.add_node("cardiovascular_agent", run_cardiovascular_agent)  # Heart diagnosis (RAG)
builder.add_node("neurological_agent",  run_neurological_agent)     # Neuro diagnosis (RAG)
builder.add_node("synthesis_agent",     synthesis_agent)        # Combines all findings
builder.add_node("pharmacy_finder_agent", run_pharmacy_finder_agent)  # Google Maps search

# -----------------------------------------------------------------------------
# ENTRY FLOW (fixed path)
# -----------------------------------------------------------------------------
# Every query starts with planning, then goes to supervisor for routing

builder.add_edge(START, "planner_agent")
builder.add_edge("planner_agent", "supervisor_agent")


# -----------------------------------------------------------------------------
# SUPERVISOR ROUTING (conditional edges)
# -----------------------------------------------------------------------------
# Supervisor decides which specialist to call next based on the plan
# and current conversation state

def route_supervisor(state: State) -> str:
    """
    Extract the routing decision from supervisor's output.
    
    Reads the 'next' field set by supervisor_agent and returns
    the target agent name for LangGraph to route to.
    """
    next_agent = state.get("next", "synthesis_agent")
    
    # Debug output for tracing execution flow
    print(f"\n   📍 ROUTING TO: {next_agent}")
    print(f"   📝 Total messages: {len(state.get('messages', []))}")
    
    # Show execution history
    messages = state.get('messages', [])
    agent_names = [getattr(m, 'name', '') for m in messages if hasattr(m, 'name')]
    print(f"   🤖 Agents called so far: {state.get('agents_called', [])}")
    
    return next_agent

# Map supervisor decisions to target nodes
builder.add_conditional_edges(
    "supervisor_agent",
    route_supervisor,
    {
        "patient_data_agent": "patient_data_agent",
        "cardiovascular_agent": "cardiovascular_agent",
        "neurological_agent": "neurological_agent",
        "pharmacy_finder_agent": "pharmacy_finder_agent",
        "synthesis_agent": "synthesis_agent"
    }
)

# -----------------------------------------------------------------------------
# SPECIALIST → SUPERVISOR LOOPS
# -----------------------------------------------------------------------------
# After each specialist completes, control returns to supervisor
# Supervisor then decides: call another specialist or go to synthesis

builder.add_edge("patient_data_agent",  "supervisor_agent")
builder.add_edge("cardiovascular_agent", "supervisor_agent")
builder.add_edge("neurological_agent",  "supervisor_agent")
builder.add_edge("pharmacy_finder_agent", "supervisor_agent")

# -----------------------------------------------------------------------------
# EXIT FLOW
# -----------------------------------------------------------------------------
# Only synthesis_agent can end the workflow (after combining all findings)

builder.add_edge("synthesis_agent", END)

# -----------------------------------------------------------------------------
# COMPILE GRAPH
# -----------------------------------------------------------------------------
# MemorySaver enables conversation persistence across invocations

graph = builder.compile(checkpointer=MemorySaver())


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def run_doctor_assistant(query: str):
    """
    Run the multi-agent medical workflow with the given query.
    
    Args:
        query: User's medical question or symptom description.
    
    Returns:
        Final state containing all messages and the synthesis report.
    """
    config = {"configurable": {"thread_id": "medical-case-001"}}
    result = graph.invoke(
        {"messages": [("user", query)]},
        config=config
    )
    return result


def print_response(result):
    """
    Format and print the final synthesis report.
    
    Extracts the last message (from synthesis_agent) and displays it.
    """
    print("\n" + "="*70)
    print("FINAL SYNTHESIS REPORT")
    print("="*70)
    if result.get("messages"):
        print(result["messages"][-1].content)
    print("="*70 + "\n")


# =============================================================================
# VISUALIZATION + EXAMPLE RUN (execute directly to test)
# =============================================================================

if __name__ == "__main__":
    # Export graph as PNG (shows Planner → Supervisor → Specialists flow)
    graph_image = graph.get_graph().draw_mermaid_png()
    with open("medical_multiagent_graph.png", "wb") as f:
        f.write(graph_image)
    print("✅ Graph visualization saved as medical_multiagent_graph.png")

    # Run example query
    config = {"configurable": {"thread_id": "medical-case-001"}}

    user_query = "Salma Rami needs to find nearby pharmacies within 5000 meters to buy his medications. He is driving."
    print("🚀 Starting multi-agent medical workflow...\n")
    result = graph.invoke(
        {"messages": [("user", user_query)]},
        config=config
    )

    # Display final report
    print("\n" + "="*70)
    print("FINAL SYNTHESIS REPORT")
    print("="*70)
    print(result["messages"][-1].content)