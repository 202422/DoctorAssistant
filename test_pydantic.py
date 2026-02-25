# test_pydantic.py
from typing import Annotated, List, Literal
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    step_number: int
    agent: Literal["a", "b"]
    task: Annotated[str, Field(description="test")]

print("Successfully defined PlanStep")