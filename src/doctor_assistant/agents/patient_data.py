# patient_data_agent.py
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

from ..prompts import PATIENT_DATA_THINK_PROMPT   # ← UPDATE THIS PROMPT (see below)
from ..config import get_llm
from ..mcp.neon_tools import neon_tools
from ..state import State                     # ← your shared state.py


# ============================================================================
# ERROR HANDLING MIDDLEWARE (kept exactly as you had it)
# ============================================================================

@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors with custom messages."""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"Tool error: {str(e)}. Please check your input and try again.",
            tool_call_id=request.tool_call["id"]
        )


# ============================================================================
# AGENT SETUP (ReAct agent stays exactly the same)
# ============================================================================

llm = get_llm(temperature=0, model="gpt-5.2")  # Use the same model as the main LLM for consistency

checkpointer = MemorySaver()

patient_data_agent = create_react_agent(
    model=llm,
    tools=neon_tools,
    prompt=PATIENT_DATA_THINK_PROMPT,
    checkpointer=checkpointer,
)


# ============================================================================
# NEW: LANGGRAPH NODE THAT USES THE FULL STATE
# ============================================================================

def run_patient_data_agent(state: State):
    """
    This is the node you will import into your main graph.py
    It receives the FULL conversation history (planner + plan + previous agents)
    """
    # Pass the entire messages list so the agent can see:
    # - Query Analysis
    # - Step-by-Step Plan
    # - Its own assigned task
    result = patient_data_agent.invoke(
        {"messages": state["messages"]},                     # ← THIS IS THE KEY CHANGE
        config={"configurable": {"thread_id": "patient_data_thread"}}
    )

    # Return only the last message (standard LangGraph node pattern)
    return {"messages": [result["messages"][-1]],
            "agents_called": state.get("agents_called", []) + ["patient_data_agent"]}


# ============================================================================
# Optional: Keep your old standalone runner for testing
# ============================================================================

def patient_data_node(query: str, patient_id: int | None = None, patient_name: str | None = None):
    """Keep this for quick standalone testing if you want"""
    user_message = f"""## User Query:
{query}

## Known Information:
- Patient ID: {patient_id}
- Patient Name: {patient_name}
"""

    thread_id = f"patient-{patient_id}" if patient_id else f"patient-{hash(patient_name or '')}"
    config = {"configurable": {"thread_id": thread_id}}

    result = patient_data_agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config
    )
    return result["messages"][-1].content


# ============================================================================
# Save graph visualization (kept your original)
# ============================================================================

if __name__ == "__main__":
    graph_image = patient_data_agent.get_graph().draw_mermaid_png()
    with open("patient_data_agent_graph.png", "wb") as f:
        f.write(graph_image)
    print("Graph saved as patient_data_agent_graph.png")

    # Example standalone test
    response = patient_data_node(
        query="Retrieve full clinical profile",
        patient_name="Youssef Kabbaj"
    )
    print("\nFinal Structured Output:\n")
    print(response)