from PIL import report
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from ..state import State
from ..prompts import SYNTHESIS_PROMPT
from ..config import get_llm

llm = get_llm(temperature=0.3, model="gpt-4.1-nano")  
def synthesis_agent(state: State):
    system_prompt = SYNTHESIS_PROMPT   # ← use the constant above
    
    response = llm.invoke([
        ("system", system_prompt),
        *state["messages"]
    ])

    return {
    "messages": [AIMessage(content=response.content, name="synthesis_agent")],
    "agents_called": state.get("agents_called", []) + ["synthesis_agent"]
}