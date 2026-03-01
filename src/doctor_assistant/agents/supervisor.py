"""
Supervisor Agent Module for Doctor Assistant Multi-Agent System.

The Supervisor is the central router that orchestrates specialist agents.
It follows the Planner's execution plan and decides which agent to call next
based on the current conversation state.

Flow: Planner → Supervisor → [Specialist Agents] → Supervisor → ... → Synthesis
"""

from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..config import get_llm
from ..prompts import SUPERVISOR_LLM_PROMPT
from ..state import State


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Supervisor uses structured output for reliable routing decisions
llm = get_llm(temperature=0, model="gpt-5.2")  # temperature=0 for deterministic routing


# =============================================================================
# ROUTING SCHEMA
# =============================================================================

class Route(BaseModel):
    """
    Structured output schema for supervisor routing decisions.
    
    Forces the LLM to return a valid agent name and reasoning,
    preventing hallucinated or invalid routing targets.
    """
    next: Literal[
        "patient_data_agent",      # Fetches patient records from Neon DB
        "cardiovascular_agent",    # RAG-based heart condition diagnosis
        "neurological_agent",      # RAG-based neurological diagnosis
        "pharmacy_finder_agent",   # Locates nearby pharmacies via Google Maps
        "synthesis_agent",         # Combines all findings into final response
    ]
    reason: str = Field(
        ...,
        description="Short explanation of why this agent is next",
    )


# =============================================================================
# SUPERVISOR AGENT
# =============================================================================

def supervisor_agent(state: State) -> dict:
    """
    Central router that coordinates the multi-agent workflow.
    
    Responsibilities:
    1. Analyze current conversation state and planner's instructions
    2. Decide which specialist agent should act next
    3. Track execution history (agents_called)
    4. Route to synthesis_agent when all tasks are complete
    
    Args:
        state: Current graph state containing messages and execution history.
    
    Returns:
        Dict with:
        - next: Name of the next agent to invoke
        - agents_called: Updated list of agents that have been called
    """
    # Wrap LLM with structured output for type-safe routing
    structured_llm = llm.with_structured_output(Route)

    # Get routing decision from LLM
    decision: Route = structured_llm.invoke([
        ("system", SUPERVISOR_LLM_PROMPT),
        *state["messages"],  # Include full conversation history
    ])

    print(f"🔀 Supervisor → {decision.next} | Reason: {decision.reason}")

    # Return routing decision and update execution history
    return {
        "next": decision.next,
        "agents_called": state.get("agents_called", []) + ["supervisor_agent"],
    }