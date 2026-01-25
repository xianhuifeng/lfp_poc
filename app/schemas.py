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
    user_answers: Optional[Dict[str, str]] = Field(default=None,description="User-provided answers keyed by clarification question id"
)


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

# ---------- 2.4 Clarification Manager ----------
NextAction = Literal["wait_for_user", "proceed_with_assumptions"]

class ClarificationPolicy(BaseModel):
    max_questions: int = 3
    allow_proceed_with_assumptions: bool = True


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    required: bool = False
    affects: List[str] = Field(default_factory=list)
    default_assumption: Optional[str] = None


class ClarificationOutput(BaseModel):
    question_set: List[ClarificationQuestion]
    stop_condition: List[str] = Field(
        description="IDs of questions that must be answered before proceeding"
    )
    next_action: NextAction


# ---------- API request/response ----------
class DraftRequest(BaseModel):
    text: str
    # Optional placeholders for future: context/policy
    context: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None

class DraftResponse(BaseModel):
    preprocess: PreprocessOutput
    drafting: DraftEngineOutput
    clarification: Optional[ClarificationOutput] = None


# -----------------------------
# Resume / User Answers
# -----------------------------

class ResumeRequest(BaseModel):
    draft_lfo: DraftLogFrame 
    question_set: List[ClarificationQuestion] = Field(default_factory=list)
    answers: Dict[str, str] = Field(default_factory=dict)
    policy: ClarificationPolicy = Field(default_factory=ClarificationPolicy)


class ResumeResponse(BaseModel):
    draft_lfo: DraftLogFrame
    applied_answers: Dict[str, str] = Field(default_factory=dict)
    clarification: ClarificationOutput



# -----------------------------
# Refine Draft
# -----------------------------
class RefineRequest(BaseModel):
    raw_text: str
    draft_lfo: DraftLogFrame
    question_set: List[ClarificationQuestion] = Field(default_factory=list)
    answers: Dict[str, str] = Field(default_factory=dict)
    policy: ClarificationPolicy = Field(default_factory=ClarificationPolicy)

class RefineResponse(BaseModel):
    preprocess: PreprocessOutput
    drafting: DraftEngineOutput
    clarification: ClarificationOutput
