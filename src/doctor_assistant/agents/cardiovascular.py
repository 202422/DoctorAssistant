import json
from ..state import State
from langgraph.prebuilt import create_react_agent
from ..config import get_llm
from ..knowledge_bases.cardiovascular_kb import get_retriever
from langgraph.checkpoint.memory import MemorySaver
from ..prompts.diagnosis_prompts import CARDIOVASCULAR_PROMPT
from langchain_core.tools import tool


llm = get_llm(temperature=0, model="gpt-5.2")
retriever = get_retriever(k=4)

@tool
def cardio_search(query: str) -> str:
    """Search the cardiovascular medical knowledge base."""
    docs = retriever.invoke(query)
    results = "\n\n".join(doc.page_content for doc in docs)
    return results

memory_saver = MemorySaver()

agent = create_react_agent(
    llm,
    tools=[cardio_search],
    checkpointer=memory_saver,
    prompt=CARDIOVASCULAR_PROMPT
)


# -------------------------------------------------
# Helper: stream with printed steps
# -------------------------------------------------
def stream_agent_with_steps(messages: list, config: dict) -> str:
    """Stream agent execution and print each retrieval step."""
    final_content = ""
    step = 0

    for event in agent.stream(
        {"messages": messages},
        config=config,
        stream_mode="values"   # emits full state after each step
    ):
        last_msg = event["messages"][-1]
        msg_type = type(last_msg).__name__

        # Tool call: agent decided to search
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                step += 1
                print(f"\n{'='*50}")
                print(f"🔍 Retrieval Step {step}: {tc['name']}")
                print(f"   Query: {tc['args'].get('query', tc['args'])}")
                print(f"{'='*50}")

        # Tool result: what came back from the retriever
        elif msg_type == "ToolMessage":
            print(f"\n📄 Retrieved Content (Step {step}):")
            # Print a preview (first 300 chars per chunk)
            chunks = last_msg.content.split("\n\n")
            for i, chunk in enumerate(chunks, 1):
                print(f"  [{i}] {chunk[:300]}{'...' if len(chunk) > 300 else ''}")
            print()

        # Final AI response
        elif msg_type == "AIMessage" and not getattr(last_msg, "tool_calls", None):
            final_content = last_msg.content

    return final_content


# -------------------------------------------------
# Run functions
# -------------------------------------------------
def run_cardiovascular_node(query: str, patient_info: dict | None = None) -> str:
    user_message = f"""## User Query:
{query}

## Patient Info
{patient_info}
"""
    thread_id = (
        f"patient-{patient_info['patient_id']}"
        if patient_info and "patient_id" in patient_info
        else f"patient-{hash(patient_info['name']) if patient_info else 'unknown'}"
    )
    config = {"configurable": {"thread_id": thread_id}}

    return stream_agent_with_steps(
        [{"role": "user", "content": user_message}],
        config
    )


def run_cardiovascular_agent(state: State) -> dict:
    config = {"configurable": {"thread_id": "cardiovascular_thread"}}
    final_content = stream_agent_with_steps(state["messages"], config)

    # Reconstruct a minimal AIMessage for the graph
    from langchain_core.messages import AIMessage
    return {
        "messages": [AIMessage(content=final_content)],
        "agents_called": state.get("agents_called", []) + ["cardiovascular_agent"]
    }


# -------------------------------------------------
# Example usage
# -------------------------------------------------
if __name__ == "__main__":
    test_query = "I've been experiencing chest pain and shortness of breath for 2 days"
    patient_info = {
        "patient_id": "3",
        "name": "Youssef Kabbaj",
        "age": 71,
        "gender": "Male",
        "medical_history": ["Hypertension"],
        "current_medications": ["Amlodipine"],
        "allergies": ["None"],
        "location": "Clinique Ghandi"
    }
    diagnosis = run_cardiovascular_node(test_query, patient_info)
