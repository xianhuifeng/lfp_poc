from app.schemas import (
    DraftResponse,
    ClarificationPolicy,
    ClarificationQuestion,
    ResumeResponse,
    DraftLogFrame,
)
from app.engines.intake_preprocess import preprocess
from app.engines.structure_drafting import structure_draft
from app.engines.clarification_manager import clarification_manager

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

def apply_user_answers(draft_lfo: DraftLogFrame, answers: dict[str, str]) -> DraftLogFrame:
    merged = dict(draft_lfo.user_answers or {})
    merged.update(answers or {})
    draft_lfo.user_answers = merged
    return draft_lfo

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
