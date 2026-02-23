"""Planner Agent - Creates execution plan for the Supervisor."""

import re
from ..config import get_llm
from ..state.schemas import PlanStep
from ..prompts.planner_prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from ..utils import get_logger

logger = get_logger(__name__)


def parse_plan_response(response: str) -> tuple[str, str, str, list[PlanStep]]:
    """Parse planner response to extract urgency, patient_name, reasoning, and plan."""
    
    # Extract urgency
    urgency = "medium"
    urgency_match = re.search(r"URGENCY:\s*(high|medium|low)", response, re.IGNORECASE)
    if urgency_match:
        urgency = urgency_match.group(1).lower()
    
    # Extract patient name
    patient_name = None
    name_match = re.search(r"PATIENT_NAME:\s*(.+?)(?=\n|REASONING:|$)", response, re.IGNORECASE)
    if name_match:
        extracted_name = name_match.group(1).strip()
        if extracted_name.lower() not in ["unknown", "not mentioned", "n/a", "none"]:
            patient_name = extracted_name
    
    # Extract reasoning
    reasoning = ""
    reasoning_match = re.search(r"REASONING:\s*(.+?)(?=PLAN:|$)", response, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()
    
    # Extract plan steps
    plan = []
    step_pattern = r"STEP\s*(\d+):\s*(\w+)\s*\|\s*(.+?)(?=\n|$)"
    matches = re.findall(step_pattern, response, re.IGNORECASE)
    
    for match in matches:
        step_num, agent, reason = match
        agent = agent.lower().strip()
        
        # Validate agent name
        valid_agents = ["patient_data", "cardiovascular", "neurological", "pharmacy_finder"]
        if agent in valid_agents:
            plan.append(PlanStep(
                step=int(step_num),
                agent=agent,
                reason=reason.strip(),
                required=True
            ))
    
    return urgency, patient_name, reasoning, plan


def run_planner_agent(query: str) -> dict:
    """
    Run the planner agent to create an execution plan.
    
    Args:
        query: User's medical query (should contain patient name and symptoms)
        
    Returns:
        Dict with plan, urgency, patient_name, and reasoning
    """
    logger.info("📋 Running Planner Agent...")
    
    llm = get_llm(temperature=0)
    
    # Build prompt
    prompt = PLANNER_SYSTEM_PROMPT + "\n\n" + PLANNER_USER_PROMPT.format(query=query)
    
    response = llm.invoke(prompt)
    
    # Parse response
    urgency, patient_name, reasoning, plan = parse_plan_response(response.content)
    
    # Ensure patient_data is first if patient name found
    if patient_name and (not plan or plan[0]["agent"] != "patient_data"):
        plan.insert(0, PlanStep(
            step=1,
            agent="patient_data",
            reason=f"Retrieve information for patient: {patient_name}",
            required=True
        ))
        # Renumber steps
        for i, step in enumerate(plan):
            step["step"] = i + 1
    
    logger.info(f"⚡ Urgency: {urgency}")
    logger.info(f"👤 Patient Name: {patient_name or 'Not found'}")
    logger.info(f"📝 Plan: {[s['agent'] for s in plan]}")
    
    return {
        "plan": plan,
        "urgency": urgency,
        "patient_name": patient_name,
        "reasoning": reasoning
    }


def print_plan(plan_result: dict):
    """Pretty print the execution plan."""
    
    print("\n" + "=" * 50)
    print("📋 EXECUTION PLAN")
    print("=" * 50)
    print(f"⚡ Urgency: {plan_result['urgency'].upper()}")
    print(f"👤 Patient: {plan_result.get('patient_name') or 'Not identified'}")
    print(f"💭 Reasoning: {plan_result['reasoning']}")
    print("-" * 50)
    print("Steps:")
    for step in plan_result["plan"]:
        print(f"   {step['step']}. {step['agent'].upper()}")
        print(f"      └─ {step['reason']}")
    print("=" * 50)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    # Test 1: Query with patient name
    print("\nTEST 1: Query with Patient Name")
    result = run_planner_agent(
        query="John Doe has been experiencing chest pain and shortness of breath for 2 days"
    )
    print_plan(result)
    
    # Test 2: Another patient
    print("\nTEST 2: Neurological Query")
    result = run_planner_agent(
        query="Jane Smith complains of severe headaches and numbness in her left hand"
    )
    print_plan(result)
    
    # Test 3: Mixed symptoms
    print("\nTEST 3: Mixed Symptoms")
    result = run_planner_agent(
        query="Patient Robert Johnson reports chest pain, dizziness, and confusion"
    )
    print_plan(result)
    
    # Test 4: No patient name
    print("\nTEST 4: No Patient Name")
    result = run_planner_agent(
        query="I have a severe headache and blurry vision"
    )
    print_plan(result)