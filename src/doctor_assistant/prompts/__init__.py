"""Prompts module."""

from .diagnosis_prompts import (
    CARDIOVASCULAR_PROMPT
)

from .synthesis_prompts import (
    SYNTHESIS_PROMPT)

from .patient_prompts import (
    PATIENT_DATA_THINK_PROMPT
)

from .planner_prompts import (
    PLANNER_SYSTEM_PROMPT
)

from .supervisor_prompts import (
    SUPERVISOR_LLM_PROMPT
)

from .pharmacy_prompts import (
    PHARMACY_SYSTEM_PROMPT,
)

__all__ = ["PHARMACY_SYSTEM_PROMPT", "SYNTHESIS_PROMPT",
    "CARDIOVASCULAR_PROMPT",
    "NEUROLOGICAL_PROMPT",
    "PATIENT_DATA_THINK_PROMPT",
    "PLANNER_SYSTEM_PROMPT",
    "SUPERVISOR_LLM_PROMPT"
]