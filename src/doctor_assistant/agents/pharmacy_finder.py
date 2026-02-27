# pharmacy_finder.py
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

from ..prompts import PHARMACY_SYSTEM_PROMPT   # ← UPDATE THIS PROMPT (see below)
from ..config import get_llm
from ..mcp import google_map_tools
from ..state import State 
from src.doctor_assistant.tools.pharmacy_tools import non_mcp_tools

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

llm = get_llm(temperature=0)

checkpointer = MemorySaver()

all_tools = non_mcp_tools + google_map_tools
for t in all_tools:
    print(t.name, type(t), getattr(t, "args_schema", None))

pharmacy_finder_agent = create_react_agent(
    model=llm,
    tools=all_tools,
    prompt=PHARMACY_SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


# ============================================================================
# NEW: LANGGRAPH NODE THAT USES THE FULL STATE
# ============================================================================

def run_pharmacy_finder_agent(state: State):
    """
    This is the node you will import into your main graph.py
    It receives the FULL conversation history (planner + plan + previous agents)
    """
    # Pass the entire messages list so the agent can see:
    # - Query Analysis
    # - Step-by-Step Plan
    # - Its own assigned task
    result = pharmacy_finder_agent.invoke(
        {"messages": state["messages"]},                     # ← THIS IS THE KEY CHANGE
        config={"configurable": {"thread_id": "pharmacy_finder_thread"}}
    )

    # Return only the last message (standard LangGraph node pattern)
    return {"messages": [result["messages"][-1]],
            "agents_called": state.get("agents_called", []) + ["pharmacy_finder_agent"]}


# ============================================================================
# Save graph visualization (kept your original)
# ============================================================================

if __name__ == "__main__":
    graph_image = pharmacy_finder_agent.get_graph().draw_mermaid_png()
    with open("pharmacy_finder_agent_graph.png", "wb") as f:
        f.write(graph_image)
    print("Graph saved as pharmacy_finder_agent_graph.png")

    # ========================================================================
    # EXAMPLE TEST CASE
    # ========================================================================
    print("\n" + "=" * 70)
    print("🧪 PHARMACY FINDER AGENT TEST")
    print("=" * 70)

    # Simulate a message history with patient context and pharmacy needs
    test_messages = [
        {
            "role": "user",
            "content": """
    Patient: Youssef Kabbaj
    Location: CHU Ibn Rochd, Casablanca, Morocco
    
    
    Task: Find nearby pharmacies in around 5000 meters. I'm driving.
            """
        }
    ]

    # Create a sample state for the node
    sample_state: State = {
        "messages": test_messages,
    }

    # Run the pharmacy finder agent node
    print("\n📍 Finding pharmacies with medications...")
    result = run_pharmacy_finder_agent(sample_state)
    
    print("\n" + "=" * 70)
    print("🏥 PHARMACIES FOUND")
    print("=" * 70)
    
    # Extract and display the final response
    if result["messages"]:
        final_message = result["messages"][-1]
        if hasattr(final_message, "content"):
            print(final_message.content)
        else:
            print(final_message)
    
    print(f"\n✅ Agents called: {', '.join(result.get('agents_called', []))}")