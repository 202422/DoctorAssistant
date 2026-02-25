from pydantic import BaseModel, Field
from typing import List, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from ..state import State, MedicalPlan, PlanStep  # your shared state file
from ..prompts import PLANNER_SYSTEM_PROMPT
from ..config import get_llm


llm = get_llm(temperature=0)  # deterministic output for planning



# ====================== PLANNER NODE ======================
def planner_agent(state: State):
    """Analyzes the request and outputs a clear, human-readable plan"""
    

    structured_llm = llm.with_structured_output(MedicalPlan)
    
    plan: MedicalPlan = structured_llm.invoke([
        ("system", PLANNER_SYSTEM_PROMPT),
        *state["messages"]
    ])

    # Convert to nice readable markdown for the team (kept in history)
    plan_text = f"**Medical Query Analysis**\n{plan.analysis}\n\n**Step-by-Step Plan**\n\n"
    
    for step in plan.steps:
        agent_name = step.agent.replace("_", " ").title() + " Agent"
        plan_text += f"{step.step_number}. **{agent_name}**\n"
        plan_text += f"   Task: {step.task}\n"
        plan_text += f"   Purpose: {step.purpose}\n\n"
    
    plan_text += f"**Final Note**\n{plan.final_note}"

    return {"messages": [AIMessage(content=plan_text)]}