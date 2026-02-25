# ========================================================
# graph.py - Main Multi-Agent Medical Workflow
# ========================================================

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import State

# ========================================================
# Import all nodes
# ========================================================
from planner_agent import planner_node
from supervisor import supervisor_node          # ← returns Command(goto=...)
from synthesis_agent import synthesis_node

from patient_data_agent import patient_data_node
from cardiovascular_agent import cardiovascular_node
from neurological_agent import neurological_node

# ========================================================
# Build the graph (exactly as in your diagram)
# ========================================================
builder = StateGraph(State)

# Nodes
builder.add_node("planner",       planner_node)
builder.add_node("supervisor",    supervisor_node)
builder.add_node("patient_data",  patient_data_node)
builder.add_node("cardiovascular", cardiovascular_node)
builder.add_node("neurological",  neurological_node)
builder.add_node("synthesis",     synthesis_node)

# Fixed entry flow
builder.add_edge(START, "planner")
builder.add_edge("planner", "supervisor")

# === ROUTING FROM SUPERVISOR ===
# No add_edge / add_conditional_edges here!
# Because supervisor_node returns Command(goto=next_agent),
# LangGraph automatically routes to whichever agent is chosen
# (patient_data, cardiovascular, neurological, or synthesis)

# Loops: specialists always give control back to supervisor
builder.add_edge("patient_data",  "supervisor")
builder.add_edge("cardiovascular", "supervisor")
builder.add_edge("neurological",  "supervisor")

# Only synthesis ends the workflow
builder.add_edge("synthesis", END)

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

    user_query = "65-year-old male with chest pain radiating to left arm and recent dizziness. What should we do?"

    print("🚀 Starting multi-agent medical workflow...\n")
    result = graph.invoke(
        {"messages": [("user", user_query)]},
        config=config
    )

    print("\n" + "="*70)
    print("FINAL SYNTHESIS REPORT")
    print("="*70)
    print(result["messages"][-1].content)