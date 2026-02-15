import json
import re
from typing import List

from openai import OpenAI

from app.prompts import SYSTEM_PROMPT_AMEND, USER_PROMPT_AMEND
from app.schemas import (
    AmendmentDraftInput,
    AmendmentDraftOutput,
    AmendmentSuggestion,
    DraftLogFrame,
    StatementRef,
)

client = OpenAI()


def _clamp_list(values: List[str], max_items: int = 5) -> List[str]:
    if not isinstance(values, list):
        return []
    return values[:max_items]


def _sanitize_amended_draft(data: dict) -> dict:
    # Keep the same cardinality constraints as the rest of the app.
    data["outcomes"] = _clamp_list(data.get("outcomes", []), 5)
    data["inputs"] = _clamp_list(data.get("inputs", []), 10)
    return data


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z']+", (text or "").lower()))


def _jaccard(a: str, b: str) -> float:
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta or not tb:
        return 0.0
    union = ta | tb
    if not union:
        return 0.0
    return len(ta & tb) / len(union)


def _suggestion_confidence(amendment_text: str, current_text: str, suggested_text: str) -> float:
    # Blend amendment relevance + actual change magnitude.
    amend_overlap = _jaccard(amendment_text, suggested_text)
    change_magnitude = 1.0 - _jaccard(current_text, suggested_text)
    score = 0.25 + (0.55 * amend_overlap) + (0.20 * change_magnitude)
    return round(max(0.0, min(1.0, score)), 3)


def _propose_amended_draft_with_llm(payload: AmendmentDraftInput) -> DraftLogFrame:
    draft_json = payload.draft_lfo.model_dump_json(indent=2)
    raw_text = payload.raw_text or ""
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_AMEND},
            {
                "role": "user",
                "content": USER_PROMPT_AMEND.format(
                    raw_text=raw_text,
                    draft_json=draft_json,
                    amendment_text=payload.amendment_text,
                ),
            },
        ],
    )

    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        data = _sanitize_amended_draft(data)
        return DraftLogFrame(**data)
    except Exception as e:
        raise ValueError(f"Invalid amendment JSON: {e}\nRaw output:\n{content}")


def _diff_to_suggestions(current: DraftLogFrame, amended: DraftLogFrame, amendment_text: str) -> List[AmendmentSuggestion]:
    suggestions: List[AmendmentSuggestion] = []
    suggestion_idx = 0

    if current.goal.strip() != amended.goal.strip():
        suggestions.append(
            AmendmentSuggestion(
                id=f"amd-goal-{suggestion_idx}",
                target=StatementRef(level="goal", index=0, text=current.goal),
                current_text=current.goal,
                suggested_text=amended.goal,
                rationale="Amendment updates the goal statement.",
                safe_to_apply=True,
                confidence=_suggestion_confidence(amendment_text, current.goal, amended.goal),
            )
        )
        suggestion_idx += 1

    if current.purpose.strip() != amended.purpose.strip():
        suggestions.append(
            AmendmentSuggestion(
                id=f"amd-purpose-{suggestion_idx}",
                target=StatementRef(level="purpose", index=0, text=current.purpose),
                current_text=current.purpose,
                suggested_text=amended.purpose,
                rationale="Amendment updates the purpose statement.",
                safe_to_apply=True,
                confidence=_suggestion_confidence(amendment_text, current.purpose, amended.purpose),
            )
        )
        suggestion_idx += 1

    max_outcomes = min(len(current.outcomes), len(amended.outcomes))
    for i in range(max_outcomes):
        if current.outcomes[i].strip() != amended.outcomes[i].strip():
            suggestions.append(
                AmendmentSuggestion(
                    id=f"amd-outcome-{i}-{suggestion_idx}",
                    target=StatementRef(level="outcome", index=i, text=current.outcomes[i]),
                    current_text=current.outcomes[i],
                    suggested_text=amended.outcomes[i],
                    rationale="Amendment updates this outcome.",
                    safe_to_apply=True,
                    confidence=_suggestion_confidence(amendment_text, current.outcomes[i], amended.outcomes[i]),
                )
            )
            suggestion_idx += 1

    max_inputs = min(len(current.inputs), len(amended.inputs))
    for i in range(max_inputs):
        if current.inputs[i].strip() != amended.inputs[i].strip():
            suggestions.append(
                AmendmentSuggestion(
                    id=f"amd-input-{i}-{suggestion_idx}",
                    target=StatementRef(level="input", index=i, text=current.inputs[i]),
                    current_text=current.inputs[i],
                    suggested_text=amended.inputs[i],
                    rationale="Amendment updates this input.",
                    safe_to_apply=True,
                    confidence=_suggestion_confidence(amendment_text, current.inputs[i], amended.inputs[i]),
                )
            )
            suggestion_idx += 1

    return suggestions


def propose_amendment_suggestions(payload: AmendmentDraftInput) -> AmendmentDraftOutput:
    amended = _propose_amended_draft_with_llm(payload)
    suggestions = _diff_to_suggestions(payload.draft_lfo, amended, payload.amendment_text)
    return AmendmentDraftOutput(suggestions=suggestions)
