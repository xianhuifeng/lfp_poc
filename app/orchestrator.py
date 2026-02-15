from app.schemas import (
    DraftResponse,
    ClarificationPolicy,
    ClarificationQuestion,
    ResumeResponse,
    DraftLogFrame,
    RefineResponse,
    ObjectiveClassifierInput,
    ObjectiveClassifierOutput,
    CausalLogicInput,
    CausalLogicOutput,
    AmendmentDraftInput,
    AmendmentDraftOutput,
)
from app.engines.intake_preprocess import preprocess
from app.engines.structure_drafting import structure_draft, refine_draft
from app.engines.clarification_manager import clarification_manager
from app.engines.objective_classifier import objective_classifier_engine
from app.engines.causal_logic_engine import causal_logic_engine
from app.engines.amendment_engine import propose_amendment_suggestions

# Helper function to run the pipeline
def run_pipeline(raw_text: str) -> DraftResponse:
    p = preprocess(raw_text)
    d = structure_draft(p.normalized_input)

    clarification = clarification_manager(
        open_questions=[
            ClarificationQuestion(id=f"q{i}", question=q, required=_is_blocking_question(q))
            for i, q in enumerate(d.open_questions)
        ],
        policy=ClarificationPolicy(),
    )

    return DraftResponse(preprocess=p, drafting=d, clarification=clarification)

# Helper function to apply user answers to the draft log frame
def apply_user_answers(draft_lfo: DraftLogFrame, answers: dict[str, str]) -> DraftLogFrame:
    merged = dict(draft_lfo.user_answers or {})
    merged.update(answers or {})
    return draft_lfo.model_copy(update={"user_answers": merged})
# Helper function to resume the pipeline with user answers
def resume_with_answers(
    draft_lfo: DraftLogFrame,
    question_set: list[ClarificationQuestion],
    answers: dict[str, str],
    policy: ClarificationPolicy,
) -> ResumeResponse:
    updated = apply_user_answers(draft_lfo, answers)
    # Only block on required questions that are still unanswered
    answered_ids = set((updated.user_answers or {}).keys())

    unanswered_required = [
        q for q in question_set
        if q.required and q.id not in answered_ids
    ]

    if unanswered_required:
        clarification = clarification_manager(open_questions=unanswered_required, policy=policy)
    else:
        # No required questions are missing; we can proceed.
        clarification = clarification_manager(open_questions=[], policy=policy)

    return ResumeResponse(draft_lfo=updated, applied_answers=answers, clarification=clarification)

# Helper function to determine if a question is blocking
def _is_blocking_question(q: str) -> bool:
    q_lower = q.lower()
    return any(keyword in q_lower for keyword in [
        "timeframe",
        "timeline",
        "by when",
        "measure",
        "metric",
        "how will you measure",
        "who is responsible",
    ])


def run_refine(raw_text: str, draft_lfo: DraftLogFrame,
               question_set: list[ClarificationQuestion],
               answers: dict[str, str],
               policy: ClarificationPolicy) -> RefineResponse:
    p = preprocess(raw_text)  # reuse normalization
    updated = apply_user_answers(draft_lfo, answers)

    d2 = refine_draft(
        normalized_input=p.normalized_input,
        draft_lfo=updated,
        question_set=question_set,
        answers=answers,
    )

    clarification = clarification_manager(
        open_questions=[
            ClarificationQuestion(id=f"q{i}", question=q, required=_is_blocking_question(q))
            for i, q in enumerate(d2.open_questions)
        ],
        policy=policy,
    )

    return RefineResponse(preprocess=p, drafting=d2, clarification=clarification)



def run_objective_classifier(
    lfo,
    context=None,
    policy=None,
) -> ObjectiveClassifierOutput:
    payload = ObjectiveClassifierInput(
        lfo=lfo,
        context=context,
        policy=policy or {},
    )
    return objective_classifier_engine(payload)


def run_causal_logic(
    lfo,
    context=None,
    policy=None,
) -> CausalLogicOutput:
    payload = CausalLogicInput(
        lfo=lfo,
        context=context,
        policy=policy or {},
    )
    return causal_logic_engine(payload)


def run_amend_draft(
    raw_text,
    amendment_text,
    draft_lfo,
    context=None,
    policy=None,
) -> AmendmentDraftOutput:
    payload = AmendmentDraftInput(
        raw_text=raw_text,
        amendment_text=amendment_text,
        draft_lfo=draft_lfo,
        context=context,
        policy=policy,
    )
    return propose_amendment_suggestions(payload)
