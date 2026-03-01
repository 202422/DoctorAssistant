"""State schemas for the Doctor Assistant graph."""

from typing import List, Literal, Annotated, Optional
from operator import add
from pydantic import Field, BaseModel


from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# Helper types (you can also put these in a separate types.py file)
class PatientDataOutput(TypedDict):
    patient_id: str
    name: str
    age: Optional[int]
    gender: Optional[str]
    medical_history: List[str]
    current_medications: List[str]
    allergies: List[str]
    location: Optional[str]


class SuggestedDrug(TypedDict):
    """Suggested drug with details."""
    name: str
    purpose: str
    dosage: str
    notes: str

class SpecialistAssessment(TypedDict):
    agent: Literal["cardiovascular", "neurological"]
    possible_conditions: List[str]
    evidence: List[str]
    suggested_drugs: List[SuggestedDrug]  # name, purpose, dosage, notes
    recommendations: List[str]
    warning_signs: List[str]
    confidence: Literal["high", "medium", "low"]
    sources_consulted: int
    raw_response: str

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]           # keeps full conversation history
    next: str  # needed for supervisor routing
    agents_called: list[str]  # Add this to track which agents ran


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

# ============================================================
# PLAN STEP
# ============================================================

class PlanStep(BaseModel):
    step_number: int
    agent: Literal["patient_data_agent", "cardiovascular_agent", "neurological_agent", "pharmacy_finder_agent", "synthesis_agent"]
    task: Annotated[str, Field(description="Exact task this agent should perform")]
    purpose: Annotated[str, Field(description="Why this step is important")]

class MedicalPlan(BaseModel):
    analysis: str = Field(..., description="Deep analysis of the user's request")
    steps: List[PlanStep]
    final_note: str = Field(..., description="Any special instructions or caveats")


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

