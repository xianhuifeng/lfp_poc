import re
from typing import List, Tuple

from app.schemas import (
    AmendmentDraftInput,
    AmendmentDraftOutput,
    AmendmentSuggestion,
    LfoLevel,
    StatementRef,
)

INPUT_HINTS = {
    "train", "build", "create", "conduct", "hire", "budget", "tool", "system",
    "process", "document", "review", "meeting", "workflow", "resource",
}
OUTCOME_HINTS = {
    "increase", "decrease", "reduce", "improve", "faster", "slower", "adopt",
    "approved", "quality", "within", "kpi", "%", "metric", "target",
}
GOAL_HINTS = {"impact", "long-term", "organization", "system-wide", "community", "national"}


def _split_sentences(text: str) -> List[str]:
    chunks = re.split(r"[.\n;]+", text or "")
    return [c.strip() for c in chunks if c.strip()]


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


def _guess_level(sentence: str) -> LfoLevel:
    s = sentence.lower()
    if any(h in s for h in GOAL_HINTS):
        return "goal"
    if any(h in s for h in INPUT_HINTS):
        return "input"
    if any(h in s for h in OUTCOME_HINTS):
        return "outcome"
    return "purpose"


def _best_target(payload: AmendmentDraftInput, sentence: str) -> Tuple[LfoLevel, int, str]:
    lfo = payload.draft_lfo
    candidates: List[Tuple[LfoLevel, int, str]] = [
        ("goal", 0, lfo.goal),
        ("purpose", 0, lfo.purpose),
    ]
    candidates += [("outcome", i, t) for i, t in enumerate(lfo.outcomes)]
    candidates += [("input", i, t) for i, t in enumerate(lfo.inputs)]

    guessed = _guess_level(sentence)
    scored = []
    for level, idx, text in candidates:
        score = _jaccard(sentence, text)
        if level == guessed:
            score += 0.15
        scored.append((score, level, idx, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    _, level, idx, text = scored[0]
    return level, idx, text


def _merge_text(current_text: str, amendment_sentence: str) -> str:
    current = (current_text or "").strip()
    amend = amendment_sentence.strip()
    if not current:
        return amend
    if amend.lower() in current.lower():
        return current
    joiner = " " if current.endswith((".", "!", "?")) else ". "
    return f"{current}{joiner}{amend}"


def propose_amendment_suggestions(payload: AmendmentDraftInput) -> AmendmentDraftOutput:
    sentences = _split_sentences(payload.amendment_text)
    suggestions: List[AmendmentSuggestion] = []

    for i, sentence in enumerate(sentences):
        level, idx, current_text = _best_target(payload, sentence)
        suggestions.append(
            AmendmentSuggestion(
                id=f"amd-{level}-{idx}-{i}",
                target=StatementRef(level=level, index=idx, text=current_text),
                current_text=current_text,
                suggested_text=_merge_text(current_text, sentence),
                rationale="Amendment suggests updating this statement to reflect new context.",
                safe_to_apply=True,
            )
        )

    return AmendmentDraftOutput(suggestions=suggestions)
