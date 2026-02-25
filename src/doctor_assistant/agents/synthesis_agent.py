from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from ..state.schemas import State
from ..prompts import SYNTHESIS_PROMPT
from ..config import get_llm

llm = get_llm(temperature=0.3)
def synthesis_node(state: State):
    system_prompt = SYNTHESIS_PROMPT   # ← use the constant above
    
    response = llm.invoke([
        ("system", system_prompt),
        *state["messages"]
    ])

    return {"messages": [AIMessage(content=response.content)]}