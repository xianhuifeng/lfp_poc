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
    inputs: List[str] = Field(..., min_items=1, max_items=10)
    user_answers: Optional[Dict[str, str]] = Field(default=None,description="User-provided answers keyed by clarification question id")


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


# -----------------------------
# 2.5 Objective Classifier
# -----------------------------

LfoLevel = Literal["goal", "purpose", "outcome", "input"]

FindingType = Literal[
    "MIXED_LEVEL",
    "OUTCOME_AS_INPUT",
    "INPUT_AS_OUTCOME",
    "PURPOSE_AS_OUTCOME",
    "GOAL_AS_PURPOSE",
    "VAGUE_STATEMENT",
    "NOT_MEASURABLE",
    "DUPLICATE_OR_OVERLAP",
    "LEVEL_INCONSISTENT_WITH_POLICY",
]

Severity = Literal["info", "warn", "error"]

EditAction = Literal["relabel", "split", "rewrite", "delete_duplicate"]


class StatementRef(BaseModel):
    level: LfoLevel
    index: int = Field(..., ge=0)
    text: str


class Finding(BaseModel):
    type: FindingType
    severity: Severity = "warn"
    message: str
    statement: StatementRef
    evidence: Dict[str, float] = Field(
        default_factory=dict,
        description="Signals used by heuristic rules, e.g. activity_score/result_score/mixed_score."
    )


class RecommendedEdit(BaseModel):
    statement: StatementRef
    action: EditAction
    to_level: Optional[LfoLevel] = Field(
        default=None,
        description="For relabel action only"
    )
    replacement_texts: Optional[List[str]] = Field(
        default=None,
        description="For split/rewrite suggestions"
    )
    rationale: str


class IntegrityScores(BaseModel):
    structure_integrity: float = Field(..., ge=0.0, le=1.0)
    by_level: Dict[LfoLevel, float] = Field(default_factory=dict)


class ObjectiveClassifierPolicy(BaseModel):
    # Thresholds
    mixed_threshold: float = Field(default=0.20, ge=0.0, le=1.0)
    activity_threshold: float = Field(default=0.18, ge=0.0, le=1.0)
    result_threshold: float = Field(default=0.18, ge=0.0, le=1.0)

    # Behavior knobs
    allow_deliverable_as_outcome: bool = False
    flag_vague_outcomes: bool = True
    flag_not_measurable_outcomes: bool = True
    check_duplicates: bool = True

    # Scoring weights
    penalty_error: float = 0.12
    penalty_warn: float = 0.06
    penalty_info: float = 0.02

    # Control to proceed (optional for agent)
    min_structure_integrity_to_proceed: float = 0.75


class ObjectiveClassifierInput(BaseModel):
    lfo: DraftLogFrame
    context: Optional[Dict[str, Any]] = None
    policy: ObjectiveClassifierPolicy = Field(default_factory=ObjectiveClassifierPolicy)


class ObjectiveClassifierOutput(BaseModel):
    findings: List[Finding] = Field(default_factory=list)
    recommended_edits: List[RecommendedEdit] = Field(default_factory=list)
    scores: IntegrityScores

# -----------------------------
# 2.5 Objective Classifier API
# -----------------------------

class ObjectiveClassifierRequest(BaseModel):
    lfo: DraftLogFrame
    context: Optional[Dict[str, Any]] = None
    policy: ObjectiveClassifierPolicy = Field(default_factory=ObjectiveClassifierPolicy)


class ObjectiveClassifierResponse(BaseModel):
    classification: ObjectiveClassifierOutput


# -----------------------------
# 2.6 Causal Logic Engine
# -----------------------------

CausalFindingType = Literal[
    "OUTCOME_TO_PURPOSE_GAP",
    "PURPOSE_TO_GOAL_GAP",
    "INPUT_TO_OUTCOME_GAP",
    "CIRCULAR_LOGIC",
    "NON_CAUSAL_STATEMENT",
]


class CausalFinding(BaseModel):
    type: CausalFindingType
    severity: Severity = "warn"
    message: str
    from_statement: Optional[StatementRef] = None
    to_statement: Optional[StatementRef] = None
    evidence: Dict[str, float] = Field(default_factory=dict)


class CausalRewriteSuggestion(BaseModel):
    target: StatementRef
    suggested_text: str
    rationale: str


class CausalLogicScores(BaseModel):
    causal_logic: float = Field(..., ge=0.0, le=1.0)
    by_link: Dict[str, float] = Field(default_factory=dict)


class CausalLogicPolicy(BaseModel):
    # advisory-first defaults
    advisory_first: bool = True
    detect_circularity: bool = True
    detect_non_causal: bool = True

    # similarity thresholds for plausible causal links
    outcomes_to_purpose_warn_threshold: float = Field(default=0.16, ge=0.0, le=1.0)
    purpose_to_goal_warn_threshold: float = Field(default=0.14, ge=0.0, le=1.0)
    inputs_to_outcomes_warn_threshold: float = Field(default=0.12, ge=0.0, le=1.0)

    # scoring penalties
    penalty_error: float = 0.10
    penalty_warn: float = 0.04
    penalty_info: float = 0.02


class CausalLogicInput(BaseModel):
    lfo: DraftLogFrame
    context: Optional[Dict[str, Any]] = None
    policy: CausalLogicPolicy = Field(default_factory=CausalLogicPolicy)


class CausalLogicOutput(BaseModel):
    findings: List[CausalFinding] = Field(default_factory=list)
    rewrite_suggestions: List[CausalRewriteSuggestion] = Field(default_factory=list)
    scores: CausalLogicScores


# -----------------------------
# 2.6 Causal Logic API
# -----------------------------

class CausalLogicRequest(BaseModel):
    lfo: DraftLogFrame
    context: Optional[Dict[str, Any]] = None
    policy: CausalLogicPolicy = Field(default_factory=CausalLogicPolicy)


class CausalLogicResponse(BaseModel):
    analysis: CausalLogicOutput


# -----------------------------
# Amendment Suggestion Engine
# -----------------------------

class AmendmentSuggestion(BaseModel):
    id: str
    target: StatementRef
    current_text: str
    suggested_text: str
    rationale: str
    safe_to_apply: bool = True
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class AmendmentDraftInput(BaseModel):
    raw_text: Optional[str] = None
    amendment_text: str
    draft_lfo: DraftLogFrame
    context: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None


class AmendmentDraftOutput(BaseModel):
    suggestions: List[AmendmentSuggestion] = Field(default_factory=list)


class AmendDraftRequest(BaseModel):
    raw_text: Optional[str] = None
    amendment_text: str
    draft_lfo: DraftLogFrame
    context: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None


class AmendDraftResponse(BaseModel):
    suggestions: List[AmendmentSuggestion] = Field(default_factory=list)
