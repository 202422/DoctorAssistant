from pydantic import BaseModel, Field
from typing import Literal
from langchain_openai import ChatOpenAI
from ..state import State
from ..config import get_llm

llm = get_llm(temperature=0)

class Route(BaseModel):
    next: Literal[
        "patient_data_agent",
        "cardiovascular_agent",
        "neurological_agent",
        "pharmacy_finder_agent",
        "synthesis_agent"
    ]
    reason: str = Field(..., description="Short explanation of why this agent is next")

def supervisor_agent(state: State) -> dict:
    """Central router that follows the planner's plan and coordinates multi-agent execution."""
    
    system_prompt = """
You are the Supervisor Agent — the central coordinator of a multi-agent workflow.

Your ONLY job is to:
1. Follow the Step-by-Step Plan created by the Planner EXACTLY.
2. Decide which agent should act NEXT based on the plan and the current conversation state.
3. Only call agents that are still needed according to the plan.
4. When all required steps are complete → immediately route to "synthesis_agent".
5. NEVER loop forever — stop as soon as the plan is finished.

Rules you MUST follow strictly:
- Look at the most recent message containing "**Step-by-Step Plan**" — this is your guide.
- Only call an agent if its step has not yet been completed, or if the plan explicitly allows multiple calls.
- If the last message is from "synthesis_agent" (or contains a final report), DO NOT call more agents — route to END.
- Do NOT invent new steps or agents — stick strictly to the Planner's plan.
- When unsure if the plan is complete → prefer routing to "synthesis_agent" rather than looping.

Available agents (use these exact names):
- "patient_data_agent"      – retrieves structured patient information
- "cardiovascular_agent"    – analyzes cardiovascular data
- "neurological_agent"      – analyzes neurological data
- "pharmacy_finder_agent"   – retrieves and analyzes pharmacy/location data
- "synthesis_agent"         – final report generator (ONLY call when ready)

Output format:
Return ONLY valid JSON matching this schema:
{
  "next": "patient_data_agent" | "cardiovascular_agent" | "neurological_agent" | "pharmacy_finder_agent" | "synthesis_agent",
  "reason": "short explanation why you chose this next agent (1 sentence)"
}
    """

    # Wrap LLM with structured output
    structured_llm = llm.with_structured_output(Route)
    decision: Route = structured_llm.invoke([
        ("system", system_prompt),
        *state["messages"]
    ])

    print(f"🔀 Supervisor → {decision.next} | Reason: {decision.reason}")
    
    # Return next agent decision and maintain agents_called history
    return {
        "next": decision.next,
        "agents_called": state.get("agents_called", []) + ["supervisor_agent"]
    }