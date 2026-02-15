import re
from typing import Tuple, List, Dict
from app.schemas import (
    ObjectiveClassifierPolicy,
    ObjectiveClassifierInput,
    ObjectiveClassifierOutput,
    LfoLevel,
    Finding,
    FindingType,
    Severity,
    StatementRef,
    RecommendedEdit,
    EditAction,
    IntegrityScores,
)

# Heuristic dictionaries (tune over time)
ACTIVITY_TERMS = {
    "build","implement","develop","create","design","write","run","conduct",
    "train","deploy","migrate","integrate","test","validate","ask","interview",
    "collect","draft","refine","produce","deliver","ship"
}
RESULT_TERMS = {
    "improved","improve","increased","increase","reduced","reduce","enabled","enable",
    "adopted","adopt","validated","reliable","scalable","compliant","consistent",
    "accurate","approved","reviewed","accepted","working","ready","acceptance","accepted"
}
VAGUE_TERMS = {"better","good","nice","optimize","enhance","great","solid"}
APPROVAL_TERMS = {"approve", "approved", "approval", "signoff", "sign-off", "accepted", "acceptance", "buy-in"}
REVIEW_TERMS = {"review", "reviewed", "present", "presented", "demo", "demos", "evaluate", "evaluated"}

def _has_any(text: str, terms: set[str]) -> bool:
    t = (text or "").lower()
    return any(term in t for term in terms)

def _approval_split_needed(text: str) -> bool:
    return _has_any(text, APPROVAL_TERMS) and _has_any(text, REVIEW_TERMS)


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", (text or "").lower())


def _signal_scores(text: str) -> Dict[str, float]:
    toks = _tokens(text)
    if not toks:
        return {"activity": 0.0, "result": 0.0, "vague": 0.0, "len": 0.0}

    n = len(toks)
    activity = sum(1 for t in toks if t in ACTIVITY_TERMS) / n
    result = sum(1 for t in toks if t in RESULT_TERMS) / n
    vague = sum(1 for t in toks if t in VAGUE_TERMS) / n
    return {"activity": activity, "result": result, "vague": vague, "len": float(n)}


def _measurable_hint(text: str) -> bool:
    t = (text or "").lower()
    # cheap measurability signals for POC
    return any(k in t for k in ["%", "kpi", "sla", "approved", "sign-off", "validated", "tested", "review", "accept"])


def _is_mixed(sig: Dict[str, float], policy: ObjectiveClassifierPolicy) -> bool:
    # Mixed if both activity + result are non-trivial
    return (sig["activity"] >= policy.activity_threshold) and (sig["result"] >= policy.result_threshold)


def _likely_level(sig: Dict[str, float], policy: ObjectiveClassifierPolicy) -> LfoLevel:
    # Decide which "side" dominates
    if sig["activity"] >= sig["result"]:
        return "input"
    return "outcome"


def _normalize_for_dupe(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 %\-]", "", t)
    return t


def objective_classifier_engine(payload: ObjectiveClassifierInput) -> ObjectiveClassifierOutput:
    lfo = payload.lfo
    policy = payload.policy

    findings: List[Finding] = []
    edits: List[RecommendedEdit] = []

    def add_finding(level: LfoLevel, idx: int, text: str, ftype: FindingType, sev: Severity, msg: str, ev: Dict[str, float]):
        findings.append(Finding(
            type=ftype,
            severity=sev,
            message=msg,
            statement=StatementRef(level=level, index=idx, text=text),
            evidence=ev
        ))

    def add_edit(level: LfoLevel, idx: int, text: str, action: EditAction, rationale: str,
                 to_level: LfoLevel | None = None, replacement_texts: List[str] | None = None):
        edits.append(RecommendedEdit(
            statement=StatementRef(level=level, index=idx, text=text),
            action=action,
            to_level=to_level,
            replacement_texts=replacement_texts,
            rationale=rationale
        ))

    # --- Check goal/purpose (minimal) ---
    for top_level in [("goal", lfo.goal), ("purpose", lfo.purpose)]:
        level, text = top_level[0], (top_level[1] or "").strip()
        if not text:
            continue
        sig = _signal_scores(text)
        if _is_mixed(sig, policy):
            add_finding(level, 0, text, "MIXED_LEVEL", "warn",
                        f"{level} mixes activity and result signals; consider separating intent vs condition.",
                        sig)
            add_edit(level, 0, text, "split",
                     rationale="Keep goal/purpose as a condition; push implementation verbs into inputs/outcomes.",
                     replacement_texts=[
                         f"(Condition) {text}",
                         f"(Work) {text}"
                     ])

    # --- Outcomes ---
    for i, text in enumerate(lfo.outcomes):
        t = (text or "").strip()
        if not t:
            continue
        sig = _signal_scores(t)

        # NEW: approval/review combo → force split, not relabel
        if _approval_split_needed(t):
            add_finding("outcome", i, t, "MIXED_LEVEL", "error",
                        "Outcome mixes governance activity (review) with an acceptance result (approval). Split it.",
                        {**sig, "approval_rule": 1.0})
            add_edit("outcome", i, t, "split",
                    rationale="Keep approval/sign-off as Outcome; move review/demo activity to Inputs.",
                    replacement_texts=[
                        "Conduct stakeholder review / demo of the POC (Input)",
                        "POC approved by stakeholders (recorded sign-off) (Outcome)"
                    ])
            continue

        if _is_mixed(sig, policy):
            add_finding("outcome", i, t, "MIXED_LEVEL", "error",
                        "Outcome mixes activities (inputs) and results (outcomes).",
                        sig)
            add_edit("outcome", i, t, "split",
                     rationale="Split into (Input: work) + (Outcome: achieved condition).",
                     replacement_texts=[
                         f"(Input) {t}",
                         f"(Outcome) {t}"
                     ])
            continue

        likely = _likely_level(sig, policy)

        if likely == "input" and not policy.allow_deliverable_as_outcome:
            add_finding("outcome", i, t, "OUTCOME_AS_INPUT", "warn",
                        "This reads like an activity/deliverable (input) but is listed as an outcome.",
                        sig)
            add_edit("outcome", i, t, "relabel",
                     to_level="input",
                     rationale="Move activity/deliverable statements to Inputs.")
        else:
            if policy.flag_vague_outcomes and sig["vague"] >= 0.08 and not _measurable_hint(t):
                add_finding("outcome", i, t, "VAGUE_STATEMENT", "warn",
                            "Outcome is vague; add specificity or evidence.",
                            sig)
                add_edit("outcome", i, t, "rewrite",
                         rationale="Add acceptance criteria / observable evidence.",
                         replacement_texts=[f"{t} (with acceptance criteria)"])

            if policy.flag_not_measurable_outcomes and (sig["result"] >= 0.05) and not _measurable_hint(t):
                add_finding("outcome", i, t, "NOT_MEASURABLE", "warn",
                            "Outcome reads like a result but lacks measurable/observable condition.",
                            sig)
                add_edit("outcome", i, t, "rewrite",
                         rationale="Make it testable: who approves, what metric, what evidence.",
                         replacement_texts=[f"{t} (measured by ...)"])

    # --- Inputs ---
    for i, text in enumerate(lfo.inputs):
        t = (text or "").strip()
        if not t:
            continue
        sig = _signal_scores(t)

        if _is_mixed(sig, policy):
            add_finding("input", i, t, "MIXED_LEVEL", "warn",
                        "Input mixes work and result; inputs should be pure resources/activities.",
                        sig)
            add_edit("input", i, t, "split",
                     rationale="Split the work (input) from the achieved condition (outcome).",
                     replacement_texts=[
                         f"(Input) {t}",
                         f"(Outcome) {t}"
                     ])
            continue

        likely = _likely_level(sig, policy)
        if likely == "outcome":
            add_finding("input", i, t, "INPUT_AS_OUTCOME", "error",
                        "This reads like a result/state (outcome) but is listed as an input.",
                        sig)
            add_edit("input", i, t, "relabel",
                     to_level="outcome",
                     rationale="Move result/state statements to Outcomes.")

    # --- Duplicate/overlap check (simple exact-normalized match for POC) ---
    if policy.check_duplicates:
        seen = {}
        # combine all statements
        combined: List[Tuple[LfoLevel, int, str]] = []
        combined.append(("goal", 0, lfo.goal))
        combined.append(("purpose", 0, lfo.purpose))
        combined += [("outcome", i, s) for i, s in enumerate(lfo.outcomes)]
        combined += [("input", i, s) for i, s in enumerate(lfo.inputs)]

        for level, idx, text in combined:
            norm = _normalize_for_dupe(text)
            if not norm:
                continue
            if norm in seen:
                prev = seen[norm]
                add_finding(level, idx, text, "DUPLICATE_OR_OVERLAP", "warn",
                            f"Duplicate/overlap with {prev['level']}[{prev['index']}].",
                            {"duplicate": 1.0})
                add_edit(level, idx, text, "delete_duplicate",
                         rationale="Remove duplicate or rephrase to clarify distinct meaning.")
            else:
                seen[norm] = {"level": level, "index": idx}

    # --- Scoring ---
    penalty = 0.0
    for f in findings:
        if f.severity == "error":
            penalty += policy.penalty_error
        elif f.severity == "warn":
            penalty += policy.penalty_warn
        else:
            penalty += policy.penalty_info

    structure_integrity = max(0.0, 1.0 - penalty)

    # Optional per-level subscore (simple)
    by_level: Dict[LfoLevel, float] = {"goal": 1.0, "purpose": 1.0, "outcome": 1.0, "input": 1.0}
    for lvl in by_level.keys():
        lvl_pen = 0.0
        for f in findings:
            if f.statement.level == lvl:
                lvl_pen += policy.penalty_error if f.severity == "error" else policy.penalty_warn if f.severity == "warn" else policy.penalty_info
        by_level[lvl] = max(0.0, 1.0 - lvl_pen)

    return ObjectiveClassifierOutput(
        findings=findings,
        recommended_edits=edits,
        scores=IntegrityScores(
            structure_integrity=round(structure_integrity, 3),
            by_level={k: round(v, 3) for k, v in by_level.items()},
        )
    )
