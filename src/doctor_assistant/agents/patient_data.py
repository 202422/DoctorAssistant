from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage

from ..prompts import PATIENT_DATA_THINK_PROMPT
from ..config import get_llm
from ..mcp.neon_tools import neon_tools


# ============================================================================
# ERROR HANDLING MIDDLEWARE
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
# AGENT SETUP
# ============================================================================

llm = get_llm(temperature=0)

# Initialize memory for conversation persistence
checkpointer = MemorySaver()

# Create ReAct agent with LangGraph
agent = create_react_agent(
    llm,
    neon_tools,
    prompt=PATIENT_DATA_THINK_PROMPT,
    checkpointer=checkpointer 
)



# ============================================================================
# QUERY EXECUTION
# ============================================================================

def run_patient_data_agent(query: str, patient_id: int | None = None, patient_name: str | None = None):
    """
    Executes the medical ReAct agent.
    """
    
    # Build the user message with patient context
    user_message = f"""## User Query:
{query}

## Known Information:
- Patient ID: {patient_id}
- Patient Name: {patient_name}
"""
    
    # Configure thread for conversation persistence
    thread_id = f"patient-{patient_id}" if patient_id else f"patient-{hash(patient_name)}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Invoke the agent
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config
    )
    
    # Extract the final response
    return result["messages"][-1].content


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Save agent graph visualization
    graph_image = agent.get_graph().draw_mermaid_png()
    with open("patient_data_agent_graph.png", "wb") as f:
        f.write(graph_image)
    print("Graph saved as patient_data_agent_graph.png")

    # Run the agent
    response = run_patient_data_agent(
        query="Retrieve full clinical profile",
        patient_name="Youssef Kabbaj"
    )
    print("\nFinal Structured Output:\n")
    print(response)