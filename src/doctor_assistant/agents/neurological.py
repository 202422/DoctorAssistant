"""Neurological Diagnosis Agent using ReAct framework with 2 nodes."""

import re
from langgraph.graph import StateGraph, END
import sys
import os

SRC_DIR = os.path.abspath(os.path.dirname(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from ..config import get_llm
from ..knowledge_bases.neurological_kb import get_retriever
from ..state.schemas import (
    NeurologicalAgentState, 
    ReActStep, 
    DiagnosisResult,
    SuggestedDrug
)
from ..prompts import NEUROLOGICAL_THINK_PROMPT, NEUROLOGICAL_FINAL_PROMPT
from ..utils import get_logger

logger = get_logger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_patient_info(patient_info: dict) -> str:
    """Format patient info for prompt."""
    if not patient_info:
        return "No patient information available."
    
    lines = []
    for key, value in patient_info.items():
        if value:
            if isinstance(value, list):
                lines.append(f"- {key.replace('_', ' ').title()}: {', '.join(value)}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    
    return "\n".join(lines) if lines else "No patient information available."


def format_react_history(history: list[ReActStep]) -> str:
    """Format ReAct history for prompt."""
    if not history:
        return "No previous research conducted yet."
    
    formatted = []
    for i, step in enumerate(history, 1):
        formatted.append(f"""
--- Step {i} ---
Thought: {step['thought']}
Action: {step['action']}
Action Input: {step['action_input']}
Observation: {step['observation'][:500]}...
""")
    return "\n".join(formatted)


def parse_llm_response(response: str) -> tuple[str, str, str]:
    """Parse LLM response to extract thought, action, and action_input."""
    
    thought = ""
    action = "search"
    action_input = ""
    
    thought_match = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|$)", response, re.DOTALL | re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()
    
    action_match = re.search(r"ACTION:\s*(search|final_answer)", response, re.IGNORECASE)
    if action_match:
        action = action_match.group(1).lower()
    
    input_match = re.search(r"ACTION_INPUT:\s*(.+?)$", response, re.DOTALL | re.IGNORECASE)
    if input_match:
        action_input = input_match.group(1).strip()
    
    return thought, action, action_input


def parse_suggested_drugs(text: str) -> list[SuggestedDrug]:
    """Parse suggested drugs from response."""
    
    drugs = []
    
    # Find SUGGESTED_DRUGS section
    pattern = r"SUGGESTED_DRUGS:\s*\n((?:- .+\n?)+)"
    match = re.search(pattern, text, re.IGNORECASE)
    
    if not match:
        return drugs
    
    drug_lines = re.findall(r"- (.+)", match.group(1))
    
    for line in drug_lines:
        drug = SuggestedDrug(
            name="",
            purpose="",
            dosage="",
            notes=""
        )
        
        # Parse: NAME: xxx | PURPOSE: xxx | DOSAGE: xxx | NOTES: xxx
        name_match = re.search(r"NAME:\s*([^|]+)", line, re.IGNORECASE)
        if name_match:
            drug["name"] = name_match.group(1).strip()
        
        purpose_match = re.search(r"PURPOSE:\s*([^|]+)", line, re.IGNORECASE)
        if purpose_match:
            drug["purpose"] = purpose_match.group(1).strip()
        
        dosage_match = re.search(r"DOSAGE:\s*([^|]+)", line, re.IGNORECASE)
        if dosage_match:
            drug["dosage"] = dosage_match.group(1).strip()
        
        notes_match = re.search(r"NOTES:\s*(.+)$", line, re.IGNORECASE)
        if notes_match:
            drug["notes"] = notes_match.group(1).strip()
        
        # Only add if we got at least a name
        if drug["name"]:
            drugs.append(drug)
    
    return drugs


def parse_final_diagnosis(response: str, sources_consulted: int = 0) -> DiagnosisResult:
    """Parse the final diagnosis response into structured format."""
    
    def extract_list(text: str, section: str) -> list[str]:
        """Extract bullet points from a section."""
        pattern = rf"{section}:\s*\n((?:- .+\n?)+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            items = re.findall(r"- ([^|]+?)(?:\n|$)", match.group(1))
            return [item.strip() for item in items if item.strip()]
        return []
    
    def extract_value(text: str, section: str) -> str:
        """Extract single value from a section."""
        pattern = rf"{section}:\s*(.+?)(?=\n[A-Z_]+:|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    # Parse all sections
    possible_conditions = extract_list(response, "POSSIBLE_CONDITIONS")
    evidence = extract_list(response, "EVIDENCE")
    suggested_drugs = parse_suggested_drugs(response)
    recommendations = extract_list(response, "RECOMMENDATIONS")
    warning_signs = extract_list(response, "WARNING_SIGNS")
    confidence = extract_value(response, "CONFIDENCE").lower()
    
    # Validate confidence
    if confidence not in ["high", "medium", "low"]:
        confidence = "medium"
    
    return DiagnosisResult(
        agent="neurological",
        possible_conditions=possible_conditions or ["Unable to determine specific condition"],
        evidence=evidence or ["Insufficient evidence gathered"],
        suggested_drugs=suggested_drugs or [],
        recommendations=recommendations or ["Consult a healthcare professional"],
        warning_signs=warning_signs or ["Seek immediate care if symptoms worsen"],
        confidence=confidence,
        sources_consulted=sources_consulted,
        raw_response=response
    )


# ============================================================
# NODE 1: LLM NODE (Think & Decide)
# ============================================================

def llm_node(state: NeurologicalAgentState) -> NeurologicalAgentState:
    """
    LLM Node: Thinks about the query and decides next action.
    
    Reads: query, patient_info, react_history, observation
    Writes: thought, action, action_input, final_diagnosis
    """
    logger.info(f"🧠 LLM Node - Iteration {state.get('iteration', 0) + 1}")
    
    llm = get_llm(temperature=0)
    
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    # Check if max iterations reached → force final answer
    if iteration >= max_iterations:
        logger.info("⚠️ Max iterations reached. Generating final answer...")
        
        all_contexts = "\n\n---\n\n".join(state.get("retrieved_contexts", []))
        
        final_prompt = NEUROLOGICAL_FINAL_PROMPT.format(
            patient_info=format_patient_info(state.get("patient_info", {})),
            query=state["query"],
            react_history=format_react_history(state.get("react_history", [])),
            all_contexts=all_contexts if all_contexts else "No context retrieved."
        )
        
        response = llm.invoke(final_prompt)
        
        diagnosis_result = parse_final_diagnosis(response.content, iteration)
        
        return {
            **state,
            "thought": "Max iterations reached. Providing final diagnosis.",
            "action": "final_answer",
            "action_input": response.content,
            "final_diagnosis": diagnosis_result,
            "is_complete": True
        }
    
    # Normal thinking process
    prompt = NEUROLOGICAL_THINK_PROMPT.format(
        patient_info=format_patient_info(state.get("patient_info", {})),
        query=state["query"],
        react_history=format_react_history(state.get("react_history", [])),
        observation=state.get("observation", "No observation yet. This is the first step.")
    )
    
    response = llm.invoke(prompt)
    thought, action, action_input = parse_llm_response(response.content)
    
    logger.info(f"💭 Thought: {thought[:100]}...")
    logger.info(f"⚡ Action: {action}")
    logger.info(f"📝 Action Input: {action_input[:100]}...")
    
    # If final_answer, generate proper structured response
    if action == "final_answer":
        all_contexts = "\n\n---\n\n".join(state.get("retrieved_contexts", []))
        
        final_prompt = NEUROLOGICAL_FINAL_PROMPT.format(
            patient_info=format_patient_info(state.get("patient_info", {})),
            query=state["query"],
            react_history=format_react_history(state.get("react_history", [])),
            all_contexts=all_contexts if all_contexts else "No context retrieved."
        )
        
        final_response = llm.invoke(final_prompt)
        diagnosis_result = parse_final_diagnosis(final_response.content, iteration)
        
        return {
            **state,
            "thought": thought,
            "action": action,
            "action_input": final_response.content,
            "final_diagnosis": diagnosis_result,
            "is_complete": True
        }
    
    return {
        **state,
        "thought": thought,
        "action": action,
        "action_input": action_input
    }


# ============================================================
# NODE 2: KB NODE (Search Knowledge Base)
# ============================================================

def kb_node(state: NeurologicalAgentState) -> NeurologicalAgentState:
    """
    KB Node: Searches the neurological knowledge base.
    
    Reads: action_input
    Writes: observation, react_history, retrieved_contexts, iteration
    """
    search_query = state.get("action_input", state["query"])
    logger.info(f"🔍 KB Node - Searching: {search_query[:50]}...")
    
    retriever = get_retriever(k=3)
    docs = retriever.invoke(search_query)
    
    if docs:
        observation = "\n\n---\n\n".join([
            f"[Source {i+1}]\n{doc.page_content}"
            for i, doc in enumerate(docs)
        ])
    else:
        observation = "No relevant information found in the knowledge base."
    
    logger.info(f"📚 Retrieved {len(docs)} documents")
    
    react_step = ReActStep(
        thought=state.get("thought", ""),
        action=state.get("action", "search"),
        action_input=search_query,
        observation=observation[:500]
    )
    
    new_iteration = state.get("iteration", 0) + 1
    
    return {
        **state,
        "observation": observation,
        "react_history": [react_step],
        "retrieved_contexts": [observation],
        "iteration": new_iteration
    }


# ============================================================
# ROUTING FUNCTION
# ============================================================

def should_continue(state: NeurologicalAgentState) -> str:
    """Determine next node based on action."""
    
    if state.get("is_complete", False):
        logger.info("✅ Agent complete. Ending.")
        return END
    
    action = state.get("action", "search")
    
    if action == "final_answer":
        logger.info("✅ Final answer ready. Ending.")
        return END
    
    if action == "search":
        logger.info("🔄 Continuing to KB node...")
        return "kb_node"
    
    return END


# ============================================================
# BUILD THE GRAPH
# ============================================================

def create_neurological_graph() -> StateGraph:
    """Create the neurological agent graph."""
    
    graph = StateGraph(NeurologicalAgentState)
    
    graph.add_node("llm_node", llm_node)
    graph.add_node("kb_node", kb_node)
    
    graph.set_entry_point("llm_node")
    
    graph.add_conditional_edges(
        "llm_node",
        should_continue,
        {
            "kb_node": "kb_node",
            END: END
        }
    )
    
    graph.add_edge("kb_node", "llm_node")
    
    return graph.compile()


# ============================================================
# RUN FUNCTION
# ============================================================

def run_neurological_agent(query: str, patient_info: dict = None) -> DiagnosisResult:
    """
    Run the neurological agent.
    
    Args:
        query: Patient's question/symptoms
        patient_info: Patient information dict
        
    Returns:
        DiagnosisResult with structured diagnosis
    """
    
    initial_state: NeurologicalAgentState = {
        "query": query,
        "patient_info": patient_info or {},
        "action": "",
        "action_input": "",
        "observation": "",
        "thought": "",
        "react_history": [],
        "retrieved_contexts": [],
        "iteration": 0,
        "max_iterations": 3,
        "final_diagnosis": None,
        "is_complete": False
    }
    
    graph = create_neurological_graph()

    # Save graph visualization
    png_bytes = graph.get_graph().draw_mermaid_png()
    graph_path = os.path.join(SRC_DIR, "neurological_agent_graph.png")

    with open(graph_path, "wb") as f:
        f.write(png_bytes)
    
    logger.info("🧠 Starting Neurological Agent...")
    logger.info(f"📋 Query: {query}")
    
    final_state = graph.invoke(initial_state)
    
    logger.info("🧠 Neurological Agent completed!")
    
    return final_state["final_diagnosis"]


# ============================================================
# PRETTY PRINT RESULT
# ============================================================

def print_diagnosis(result: DiagnosisResult):
    """Pretty print the diagnosis result."""
    
    print("\n" + "=" * 70)
    print("🧠 NEUROLOGICAL DIAGNOSIS RESULT")
    print("=" * 70)
    
    print(f"\n📊 Confidence: {result['confidence'].upper()}")
    print(f"🔍 Sources Consulted: {result['sources_consulted']}")
    
    print("\n" + "-" * 70)
    print("🩺 POSSIBLE CONDITIONS:")
    print("-" * 70)
    for condition in result["possible_conditions"]:
        print(f"   • {condition}")
    
    print("\n" + "-" * 70)
    print("📚 EVIDENCE:")
    print("-" * 70)
    for evidence in result["evidence"]:
        print(f"   • {evidence}")
    
    print("\n" + "-" * 70)
    print("💊 SUGGESTED DRUGS:")
    print("-" * 70)
    if result["suggested_drugs"]:
        for drug in result["suggested_drugs"]:
            print(f"\n   💉 {drug['name']}")
            print(f"      Purpose: {drug['purpose']}")
            print(f"      Dosage:  {drug['dosage']}")
            if drug['notes']:
                print(f"      ⚠️ Notes:  {drug['notes']}")
    else:
        print("   No specific drugs suggested. Consult a physician.")
    
    print("\n" + "-" * 70)
    print("📋 RECOMMENDATIONS:")
    print("-" * 70)
    for rec in result["recommendations"]:
        print(f"   • {rec}")
    
    print("\n" + "-" * 70)
    print("⚠️  WARNING SIGNS (Seek Immediate Care):")
    print("-" * 70)
    for warning in result["warning_signs"]:
        print(f"   🚨 {warning}")
    
    print("\n" + "=" * 70)
    print("⚠️  DISCLAIMER: This is AI-assisted analysis.")
    print("    Neurological conditions can be serious and time-sensitive.")
    print("    Medications should only be taken under medical supervision.")
    print("    Please consult a healthcare professional immediately.")
    print("=" * 70)


# ============================================================
# TEST
# ============================================================

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
    
    result = run_neurological_agent(test_query, test_patient)
    
    print_diagnosis(result)