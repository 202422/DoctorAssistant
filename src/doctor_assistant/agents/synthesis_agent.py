from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from ..state.schemas import State
from ..prompts import SYNTHESIS_SYSTEM_PROMPT
from ..config import get_llm

llm = get_llm(temperature=0.3)

def synthesis_node(state: State):
    """Final aggregator – produces the complete clinical report"""
    

    response = llm.invoke([
        ("system", SYNTHESIS_SYSTEM_PROMPT),
        *state["messages"]
    ])

    return {"messages": [AIMessage(content=response.content)]}