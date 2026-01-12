from pydantic import BaseModel, Field
from typing import List

class DraftLogFrame(BaseModel):
    goal: str = Field(..., description="High-level impact")
    purpose: str = Field(..., description="Immediate objective")
    outcomes: List[str] = Field(..., min_items=1, max_items=5)
    inputs: List[str] = Field(..., min_items=1, max_items=5)

class DraftResponse(BaseModel):
    draft_lfo: DraftLogFrame
    confidence: float = Field(..., ge=0.0, le=1.0)
    questions: List[str] = Field(default_factory=list, max_items=5)
