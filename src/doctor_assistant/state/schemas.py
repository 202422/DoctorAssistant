"""State schemas for the Doctor Assistant graph."""

from typing import TypedDict, Literal, Annotated
from operator import add


class PatientInfo(TypedDict, total=False):
    """Patient information structure."""
    patient_id: str
    name: str
    age: int
    gender: str
    medical_history: list[str]
    current_medications: list[str]
    allergies: list[str]
    location: str


class SuggestedDrug(TypedDict):
    """Suggested drug with details."""
    name: str
    purpose: str
    dosage: str
    notes: str


class DiagnosisResult(TypedDict):
    """Structured diagnosis result."""
    agent: str
    possible_conditions: list[str]
    evidence: list[str]
    suggested_drugs: list[SuggestedDrug]
    recommendations: list[str]
    warning_signs: list[str]
    confidence: str
    sources_consulted: int
    raw_response: str


class ReActStep(TypedDict):
    """Single ReAct step record."""
    thought: str
    action: str
    action_input: str
    observation: str


# ============================================================
# PLAN STEP
# ============================================================

class PlanStep(TypedDict):
    """A single step in the execution plan."""
    step: int
    agent: Literal["patient_data", "cardiovascular", "neurological", "pharmacy_finder"]
    reason: str
    required: bool


# ============================================================
# PLANNER STATE
# ============================================================

class PlannerState(TypedDict, total=False):
    """State for Planner Agent."""
    
    # Input
    query: str
    patient_name: str | None  # Changed from patient_id
    
    # Output
    plan: list[PlanStep]
    urgency: Literal["high", "medium", "low"]
    reasoning: str


# ============================================================
# SUPERVISOR STATE
# ============================================================

class SupervisorState(TypedDict, total=False):
    """State for Supervisor Agent."""
    
    # === Input from Planner ===
    query: str
    patient_name: str | None  # Changed from patient_id
    plan: list[PlanStep]
    urgency: str
    
    # === Execution Control ===
    current_step: int
    next_agent: Literal["llm", "patient_data", "cardiovascular", "neurological", "end"] | None
    
    # === Collected Data ===
    patient_info: PatientInfo | None
    diagnosis_results: Annotated[list[DiagnosisResult], add]
    
    # === LLM Node Outputs ===
    thought: str
    should_continue: bool
    
    # === Final Output ===
    final_response: str
    is_complete: bool
    error: str | None


# ============================================================
# MAIN GRAPH STATE
# ============================================================

class MainGraphState(TypedDict, total=False):
    """State for the main Doctor Assistant graph."""
    
    # === User Input ===
    query: str
    patient_name: str | None  # Changed from patient_id
    
    # === Planner Output ===
    plan: list[PlanStep]
    urgency: str
    planner_reasoning: str
    
    # === Supervisor Execution ===
    current_step: int
    next_agent: str | None
    thought: str
    
    # === Collected Data ===
    patient_info: PatientInfo | None
    diagnosis_results: Annotated[list[DiagnosisResult], add]
    
    # === Final Output ===
    final_response: str
    is_complete: bool
    error: str | None


# ============================================================
# SUB-AGENT STATES
# ============================================================

class PatientDataAgentState(TypedDict, total=False):
    """State for Patient Data Agent."""
    query: str
    patient_id: int | None
    patient_name: str | None
    patient_info: PatientInfo | None
    is_complete: bool
    error: str | None


class CardiovascularAgentState(TypedDict, total=False):
    """State for Cardiovascular ReAct Agent."""
    query: str
    patient_info: PatientInfo
    action: Literal["search", "final_answer"]
    action_input: str
    observation: str
    thought: str
    react_history: Annotated[list[ReActStep], add]
    retrieved_contexts: Annotated[list[str], add]
    iteration: int
    max_iterations: int
    final_diagnosis: DiagnosisResult
    is_complete: bool


class NeurologicalAgentState(TypedDict, total=False):
    """State for Neurological ReAct Agent."""
    query: str
    patient_info: PatientInfo
    action: Literal["search", "final_answer"]
    action_input: str
    observation: str
    thought: str
    react_history: Annotated[list[ReActStep], add]
    retrieved_contexts: Annotated[list[str], add]
    iteration: int
    max_iterations: int
    final_diagnosis: DiagnosisResult
    is_complete: bool