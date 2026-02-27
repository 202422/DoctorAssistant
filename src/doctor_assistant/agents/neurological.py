from ..state import State
from langgraph.prebuilt import create_react_agent
from ..config import get_llm
from ..knowledge_bases.neurological_kb import get_retriever
from langgraph.checkpoint.memory import MemorySaver
from ..prompts.diagnosis_prompts import NEUROLOGICAL_PROMPT
from langchain_core.tools import tool
from langchain_core.messages import AIMessage


llm = get_llm(temperature=0, model="gpt-5.2")
retriever = get_retriever(k=4)

@tool
def neurological_search(query: str) -> str:
    """Search the neurological medical knowledge base."""
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

memory_saver = MemorySaver()

agent = create_react_agent(
    llm,
    tools=[neurological_search],
    checkpointer=memory_saver,
    prompt=NEUROLOGICAL_PROMPT
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
        stream_mode="values"
    ):
        last_msg = event["messages"][-1]
        msg_type = type(last_msg).__name__

        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                step += 1
                print(f"\n{'='*50}")
                print(f"🧠 Retrieval Step {step}: {tc['name']}")
                print(f"   Query: {tc['args'].get('query', tc['args'])}")
                print(f"{'='*50}")

        elif msg_type == "ToolMessage":
            print(f"\n📄 Retrieved Content (Step {step}):")
            chunks = last_msg.content.split("\n\n")
            for i, chunk in enumerate(chunks, 1):
                print(f"  [{i}] {chunk[:300]}{'...' if len(chunk) > 300 else ''}")
            print()

        elif msg_type == "AIMessage" and not getattr(last_msg, "tool_calls", None):
            final_content = last_msg.content

    return final_content


# -------------------------------------------------
# Run functions
# -------------------------------------------------
def run_neurological_node(query: str, patient_info: dict | None = None) -> str:
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


def run_neurological_agent(state: State) -> dict:
    config = {"configurable": {"thread_id": "neurological_thread"}}
    final_content = stream_agent_with_steps(state["messages"], config)

    return {
        "messages": [AIMessage(content=final_content)],
        "agents_called": state.get("agents_called", []) + ["neurological_agent"]
    }


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

    diagnosis = run_neurological_node(test_query, test_patient)
    print(diagnosis)