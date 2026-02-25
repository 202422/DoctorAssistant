from gradio import State
from langgraph.prebuilt import create_react_agent

from ..state import State
from ..config import get_llm
from ..knowledge_bases.neurological_kb import get_retriever
from langgraph.checkpoint.memory import MemorySaver
from ..prompts.diagnosis_prompts import NEUROLOGICAL_PROMPT
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langchain_core.tools import tool




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



# -------------------------------------------------
# Step 1: Initialize LLM and retriever
# -------------------------------------------------
llm = get_llm(temperature=0)           # Your LLM (e.g., GPT-4)
retriever = get_retriever(k=4)         # Vectorstore retriever

# Wrap retriever as a tool for the agent
retriever = get_retriever(k=4)

@tool
def neurological_search(query: str) -> str:
    """Search the neurological medical knowledge base."""
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

# Optional: memory saver to keep conversation context per patient
memory_saver = MemorySaver()

# -------------------------------------------------
# Step 2: Create the ReAct agent
# -------------------------------------------------
agent = create_react_agent(
    llm,
    tools=[neurological_search],
    checkpointer=memory_saver,
    prompt=NEUROLOGICAL_PROMPT
)


# -------------------------------------------------
# Step 3: Run function for a patient query
# -------------------------------------------------
def run_neurological_node(query: str, patient_info: dict | None = None):
    """
    Executes the neurological RAG agent for a patient.
    """
    # Build user message with patient info
    user_message = f"""## User Query:
{query}
    
## Patient Info
{patient_info}
"""

     # Configure thread for conversation persistence
    thread_id = f"patient-{patient_info['patient_id']}" if patient_info and 'patient_id' in patient_info else f"patient-{hash(patient_info['name']) if patient_info else 'unknown'}"
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke the agent
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config
        
    )

    # Extract the final structured response
    return result["messages"][-1].content



def run_neurological_agent(state: State):
    """
    This is the node you will import into your main graph.py
    It receives the FULL conversation history (planner + plan + previous agents)
    """
    # Pass the entire messages list so the agent can see:
    # - Query Analysis
    # - Step-by-Step Plan
    # - Its own assigned task
    result = agent.invoke(
        {"messages": state["messages"]},                     # ← THIS IS THE KEY CHANGE
        config={"configurable": {"thread_id": "neurological_thread"}}
    )

    # Return only the last message (standard LangGraph node pattern)
    return {"messages": [result["messages"][-1]],
            "agents_called": state.get("agents_called", []) + ["neurological_agent"]}

# -------------------------------------------------
# Example usage
# -------------------------------------------------
if __name__ == "__main__":
    test_patient = {
        "name": "Jane Smith",
        "age": 42,
        "gender": "Female",
        "medical_history": ["migraines", "anxiety"],
        "current_medications": ["sertraline", "sumatriptan as needed"],
        "allergies": ["sulfa drugs"]
    }
    
    test_query = "I've been having severe headaches with visual disturbances and numbness in my left hand for the past week"
    
    diagnosis = run_neurological_agent(test_query, test_patient)
    print(diagnosis)