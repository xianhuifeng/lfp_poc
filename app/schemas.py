from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any


# ---------- 2.2 Output ----------
Intent = Literal["create", "revise", "audit", "export", "portfolio_check"]

class EntityHints(BaseModel):
    goals: List[str] = Field(default_factory=list)
    measure_keywords: List[str] = Field(default_factory=list)
    org_terms: List[str] = Field(default_factory=list)

class PreprocessOutput(BaseModel):
    raw_input_id: str
    normalized_input: str
    intent: Intent = "create"
    entities: EntityHints = Field(default_factory=EntityHints)


# ---------- Canonical Draft LFO (minimal for POC) ----------
class DraftLogFrame(BaseModel):
    goal: str
    purpose: str
    outcomes: List[str] = Field(..., min_items=1, max_items=5)
    inputs: List[str] = Field(..., min_items=1, max_items=5)


# ---------- 2.3 Output mapping ----------
class TextMapping(BaseModel):
    # Keep it simple for POC: supporting phrases for each field
    goal_support: List[str] = Field(default_factory=list)
    purpose_support: List[str] = Field(default_factory=list)
    outcomes_support: Dict[str, List[str]] = Field(default_factory=dict)  # outcome_text -> supports
    inputs_support: Dict[str, List[str]] = Field(default_factory=dict)    # input_text -> supports

class DraftEngineOutput(BaseModel):
    draft_lfo: DraftLogFrame
    confidence: float = Field(..., ge=0.0, le=1.0)
    open_questions: List[str] = Field(default_factory=list, max_items=5)
    mapping: TextMapping = Field(default_factory=TextMapping)


# ---------- API request/response ----------
class DraftRequest(BaseModel):
    text: str
    # Optional placeholders for future: context/policy
    context: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None

class DraftResponse(BaseModel):
    preprocess: PreprocessOutput
    drafting: DraftEngineOutput
