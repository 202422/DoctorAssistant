# ========================================================
# graph.py - Main Multi-Agent Medical Workflow
# ========================================================

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import State


from .agents import planner_agent, supervisor_agent, run_patient_data_agent, run_cardiovascular_agent, run_neurological_agent, synthesis_agent  # for any additional helper functions or classes you defined in agents/__init__.py


import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# ========================================================
# Build the graph (exactly as in your diagram)
# ========================================================
builder = StateGraph(State)

# Nodes
builder.add_node("planner_agent",       planner_agent)
builder.add_node("supervisor_agent",    supervisor_agent)
builder.add_node("patient_data_agent",  run_patient_data_agent)
builder.add_node("cardiovascular_agent", run_cardiovascular_agent)
builder.add_node("neurological_agent",  run_neurological_agent)
builder.add_node("synthesis_agent",     synthesis_agent)

# Fixed entry flow
builder.add_edge(START, "planner_agent")
builder.add_edge("planner_agent", "supervisor_agent")


# === ROUTING FROM SUPERVISOR ===
# No add_edge / add_conditional_edges here!
# Because supervisor_agent returns Command(goto=next_agent),
# LangGraph automatically routes to whichever agent is chosen
# (patient_data, cardiovascular, neurological, or synthesis)

# Loops: specialists always give control back to supervisor
builder.add_edge("patient_data_agent",  "supervisor_agent")
builder.add_edge("cardiovascular_agent", "supervisor_agent")
builder.add_edge("neurological_agent",  "supervisor_agent")

# Only synthesis ends the workflow
builder.add_edge("synthesis_agent", END)

# Compile with memory
graph = builder.compile(checkpointer=MemorySaver())

# ========================================================
# Visualization + Example Run
# ========================================================
if __name__ == "__main__":
    # Save visual graph (shows the routing clearly)
    graph_image = graph.get_graph().draw_mermaid_png()
    with open("medical_multiagent_graph.png", "wb") as f:
        f.write(graph_image)
    print("✅ Graph visualization saved as medical_multiagent_graph.png")

    # Run example
    config = {"configurable": {"thread_id": "medical-case-001"}}

    user_query = "Youssef Kabbaj has chest pain radiating to left arm and recent dizziness. Diagnose"

    print("🚀 Starting multi-agent medical workflow...\n")
    result = graph.invoke(
        {"messages": [("user", user_query)]},
        config=config
    )

    print("\n" + "="*70)
    print("FINAL SYNTHESIS REPORT")
    print("="*70)
    print(result["messages"][-1].content)