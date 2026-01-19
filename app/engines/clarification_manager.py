from __future__ import annotations
from typing import List
from app.schemas import ClarificationQuestion, ClarificationPolicy, ClarificationOutput

def clarification_manager(
    open_questions: List[ClarificationQuestion],
    policy: ClarificationPolicy,
) -> ClarificationOutput:
    if not open_questions:
        return ClarificationOutput(question_set=[], stop_condition=[], next_action="proceed_with_assumptions")

    required = [q for q in open_questions if q.required]
    optional = [q for q in open_questions if not q.required]

    question_set: List[ClarificationQuestion] = []
    question_set.extend(required)
    remaining_slots = max(policy.max_questions - len(question_set), 0)
    if remaining_slots:
        question_set.extend(optional[:remaining_slots])
    question_set = question_set[: policy.max_questions]

    stop_condition = [q.id for q in required]

    if stop_condition:
        next_action = "wait_for_user"
    else:
        if question_set and not policy.allow_proceed_with_assumptions:
            next_action = "wait_for_user"
        else:
            next_action = "proceed_with_assumptions"

    return ClarificationOutput(question_set=question_set, stop_condition=stop_condition, next_action=next_action)
