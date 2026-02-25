from pydantic import BaseModel, Field
from typing import Literal
from langchain_openai import ChatOpenAI
from ..state import State
from ..config import get_llm

llm = get_llm(temperature=0)

class Route(BaseModel):
    next: Literal["patient_data_agent", "cardiovascular_agent", "neurological_agent", "synthesis_agent"]
    reason: str = Field(..., description="Short explanation of why this agent next")

def supervisor_agent(state: State) -> dict:  # Changed return type
    """Central router that follows the planner's plan"""
    
    system_prompt = """
    You are the Medical Supervisor — the central coordinator of the medical multi-agent team.

Your ONLY job is to:
1. Follow the step-by-step plan created by the planner EXACTLY.
2. Decide which agent should act NEXT based on the plan and the current state of the conversation.
3. Only call agents that are still needed according to the plan.
4. When all required steps in the plan have been completed → immediately route to "synthesis_agent".
5. NEVER loop forever — stop as soon as the plan is finished.

Rules you MUST follow strictly:

- The planner has already created a clear sequence of steps with assigned agents.
  Look at the most recent message containing "**Step-by-Step Plan**" — that is your guide.
- Only call an agent if its step has not yet been completed or if the plan explicitly says to call it multiple times.
- If the last message is from "synthesis_agent" (or contains a final report), DO NOT call any more agents — route to END.
- If all agents listed in the plan have already responded at least once (or as many times as required), go directly to "synthesis_agent".
- Do NOT call the same agent again unless the plan specifically requires multiple calls from that agent.
- Do NOT invent new steps or agents — stick to the planner's plan.
- When in doubt whether the plan is complete → prefer to go to "synthesis_agent" rather than looping.

Available agents (use these exact names):
- "patient_data_agent"   – retrieves patient records and history
- "cardiovascular_agent" – analyzes heart & vascular conditions
- "neurological_agent"   – analyzes brain & nervous system conditions
- "synthesis_agent"      – final report generator (ONLY call when ready)

Output format:
Always respond with valid JSON matching this schema:
{
  "next": "patient_data_agent" | "cardiovascular_agent" | "neurological_agent" | "synthesis_agent",
  "reason": "short explanation why you chose this next agent (1 sentence)"
}
    """

    structured_llm = llm.with_structured_output(Route)
    decision: Route = structured_llm.invoke([
        ("system", system_prompt),
        *state["messages"]
    ])

    print(f"🔀 Supervisor → {decision.next} | Reason: {decision.reason}")
    
    # Return the route as a string (for conditional_edges)
    return {"next": decision.next,
            "agents_called": state.get("agents_called", []) + ["supervisor_agent"]}  # Pass through agents_called without modification
            