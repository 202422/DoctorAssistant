from pydantic import BaseModel, Field
from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from state import State
from ..config import get_llm

llm = get_llm(temperature=0)

class Route(BaseModel):
    next: Literal["patient_data", "cardiovascular", "neurological", "synthesis"]
    reason: str = Field(..., description="Short explanation of why this agent next")

def supervisor_node(state: State) -> Command:
    """Central router that follows the planner's plan"""
    
    system_prompt = """
    You are the Medical Supervisor.
    Follow the detailed plan created by the planner above.
    Choose the next agent to call.
    You may call the same agent multiple times if the plan requires it.
    Only go to 'synthesis' when the plan says everything is ready.
    """

    structured_llm = llm.with_structured_output(Route)
    decision: Route = structured_llm.invoke([
        ("system", system_prompt),
        *state["messages"]
    ])

    print(f"🔀 Supervisor → {decision.next} | Reason: {decision.reason}")  # helpful debug

    return Command(goto=decision.next)