import re
import uuid
from app.schemas import PreprocessOutput, EntityHints, Intent

INTENT_KEYWORDS = {
    "audit": ["audit", "review", "diagnose", "evaluate", "critique", "score"],
    "revise": ["revise", "edit", "update", "improve", "refine"],
    "export": ["export", "ppt", "pdf", "word", "docx", "excel", "matrix"],
    "portfolio_check": ["portfolio", "alignment", "across projects", "dependencies"],
}

MEASURE_HINTS = ["increase", "decrease", "%", "percent", "reduce", "improve", "kpi", "metric", "measure", "baseline", "target"]
ORG_HINTS = ["team", "department", "division", "stakeholder", "leadership", "client", "vendor", "lab", "LLNL"]
REVISION_CUES = [
    "revise this", "edit this", "update this", "rewrite this", "refine this",
    "make this better", "make it less vague", "fix this logframe",
    "here is my logframe", "below is my logframe", "audit my logframe"
]

STRUCTURE_CUES_REGEX = r"\b(goal|purpose|outcome|inputs?)\s*[:\-]"

def _detect_intent(text: str) -> Intent:
    t = text.lower()

    # Strong cues first
    if any(cue in t for cue in ["export", "ppt", "pdf", "docx", "excel", "matrix"]):
        return "export"
    if any(cue in t for cue in ["audit", "review", "diagnose", "critique", "score"]):
        return "audit"
    if any(cue in t for cue in ["portfolio", "alignment", "across projects", "dependencies"]):
        return "portfolio_check"

    # Revise should require evidence of an existing artifact
    if any(cue in t for cue in REVISION_CUES) or re.search(STRUCTURE_CUES_REGEX, t):
        return "revise"

    return "create"

def _normalize(text: str) -> str:
    # minimal normalization: trim, collapse whitespace
    t = text.strip()
    t = re.sub(r"\s+", " ", t)
    return t

def _extract_entities(text: str) -> EntityHints:
    t = text
    goals = []
    # crude: capture sentences with "goal" word
    for m in re.finditer(r"(goal[:\-]?\s*)([^.]{10,120})", t, flags=re.IGNORECASE):
        goals.append(m.group(2).strip())

    measure_keywords = [kw for kw in MEASURE_HINTS if kw.lower() in t.lower()]
    org_terms = [kw for kw in ORG_HINTS if kw.lower() in t.lower()]
    return EntityHints(goals=goals[:5], measure_keywords=list(dict.fromkeys(measure_keywords))[:10], org_terms=list(dict.fromkeys(org_terms))[:10])

def preprocess(raw_user_text: str) -> PreprocessOutput:
    raw_input_id = f"RAW-{uuid.uuid4()}"
    normalized_input = _normalize(raw_user_text)
    intent = _detect_intent(normalized_input)
    entities = _extract_entities(raw_user_text)
    return PreprocessOutput(
        raw_input_id=raw_input_id,
        normalized_input=normalized_input,
        intent=intent,
        entities=entities
    )
