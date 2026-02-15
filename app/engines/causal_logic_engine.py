import re
from typing import Dict, List, Tuple

from app.schemas import (
    CausalFinding,
    CausalFindingType,
    CausalLogicInput,
    CausalLogicOutput,
    CausalLogicPolicy,
    CausalLogicScores,
    CausalRewriteSuggestion,
    LfoLevel,
    Severity,
    StatementRef,
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "we",
    "with",
}

MECHANISM_CUES = {"by", "through", "via", "using", "so", "because", "therefore", "leads", "enables"}
NON_CAUSAL_CUES = {"want", "should", "important", "nice", "better", "good", "goal is", "need to"}


def _tokenize(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z']+", (text or "").lower())
    return [t for t in toks if t not in STOPWORDS]


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_any(text: str, terms: set[str]) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in terms)


def _jaccard(a: str, b: str) -> float:
    a_set = set(_tokenize(a))
    b_set = set(_tokenize(b))
    if not a_set or not b_set:
        return 0.0
    union = a_set | b_set
    if not union:
        return 0.0
    return len(a_set & b_set) / len(union)


def _best_link_score(sources: List[str], target: str) -> float:
    if not sources or not target:
        return 0.0
    return max((_jaccard(src, target) for src in sources), default=0.0)


def _avg_best_input_outcome_score(inputs: List[str], outcomes: List[str]) -> float:
    if not outcomes:
        return 0.0
    scores = [_best_link_score(inputs, out) for out in outcomes if out.strip()]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _is_circular(a: str, b: str) -> bool:
    a_norm = _normalized(a)
    b_norm = _normalized(b)
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm:
        return True
    return _jaccard(a_norm, b_norm) >= 0.85


def _is_non_causal(text: str) -> bool:
    if not text.strip():
        return False
    # Mark as weakly causal when no mechanism cues are present but "wishful" language appears.
    return _contains_any(text, NON_CAUSAL_CUES) and not _contains_any(text, MECHANISM_CUES)


def _ref(level: LfoLevel, index: int, text: str) -> StatementRef:
    return StatementRef(level=level, index=index, text=text)


def _severity(base: Severity, policy: CausalLogicPolicy) -> Severity:
    if policy.advisory_first and base == "error":
        return "warn"
    return base


def causal_logic_engine(payload: CausalLogicInput) -> CausalLogicOutput:
    lfo = payload.lfo
    policy = payload.policy

    findings: List[CausalFinding] = []
    rewrites: List[CausalRewriteSuggestion] = []

    def add_finding(
        ftype: CausalFindingType,
        severity: Severity,
        message: str,
        evidence: Dict[str, float],
        from_statement: StatementRef | None = None,
        to_statement: StatementRef | None = None,
    ) -> None:
        findings.append(
            CausalFinding(
                type=ftype,
                severity=_severity(severity, policy),
                message=message,
                from_statement=from_statement,
                to_statement=to_statement,
                evidence=evidence,
            )
        )

    def add_rewrite(target: StatementRef, suggested_text: str, rationale: str) -> None:
        rewrites.append(
            CausalRewriteSuggestion(
                target=target,
                suggested_text=suggested_text,
                rationale=rationale,
            )
        )

    outcomes = [o.strip() for o in lfo.outcomes if (o or "").strip()]
    inputs = [i.strip() for i in lfo.inputs if (i or "").strip()]
    purpose = (lfo.purpose or "").strip()
    goal = (lfo.goal or "").strip()

    out_to_purpose = _best_link_score(outcomes, purpose)
    purpose_to_goal = _jaccard(purpose, goal)
    in_to_out = _avg_best_input_outcome_score(inputs, outcomes)

    if purpose and outcomes and out_to_purpose < policy.outcomes_to_purpose_warn_threshold:
        add_finding(
            "OUTCOME_TO_PURPOSE_GAP",
            "warn",
            "Outcomes weakly support the stated purpose; add a clearer causal bridge.",
            {"link_score": out_to_purpose},
            from_statement=_ref("outcome", 0, outcomes[0]),
            to_statement=_ref("purpose", 0, purpose),
        )
        add_rewrite(
            _ref("purpose", 0, purpose),
            f"{purpose} by {outcomes[0].lower()}",
            "Make the causal mechanism explicit between outcomes and purpose.",
        )

    if goal and purpose and purpose_to_goal < policy.purpose_to_goal_warn_threshold:
        add_finding(
            "PURPOSE_TO_GOAL_GAP",
            "warn",
            "Purpose weakly supports the goal; clarify how purpose outcomes contribute to impact.",
            {"link_score": purpose_to_goal},
            from_statement=_ref("purpose", 0, purpose),
            to_statement=_ref("goal", 0, goal),
        )
        add_rewrite(
            _ref("goal", 0, goal),
            f"{goal} through {purpose.lower()}",
            "Add an explicit purpose-to-goal linkage.",
        )

    if outcomes and inputs and in_to_out < policy.inputs_to_outcomes_warn_threshold:
        add_finding(
            "INPUT_TO_OUTCOME_GAP",
            "warn",
            "Inputs do not clearly explain how listed outcomes will be produced.",
            {"link_score": in_to_out},
            from_statement=_ref("input", 0, inputs[0]),
            to_statement=_ref("outcome", 0, outcomes[0]),
        )
        add_rewrite(
            _ref("outcome", 0, outcomes[0]),
            f"{outcomes[0]} because {inputs[0].lower()}",
            "Connect inputs to outcomes with a concrete mechanism.",
        )

    if policy.detect_circularity:
        circular_pairs: List[Tuple[LfoLevel, str, LfoLevel, str]] = [
            ("purpose", purpose, "goal", goal),
            ("outcome", outcomes[0] if outcomes else "", "purpose", purpose),
            ("input", inputs[0] if inputs else "", "outcome", outcomes[0] if outcomes else ""),
        ]
        for left_level, left_text, right_level, right_text in circular_pairs:
            if _is_circular(left_text, right_text):
                add_finding(
                    "CIRCULAR_LOGIC",
                    "error",
                    "Potential circular logic: adjacent levels repeat the same idea without a causal step.",
                    {"similarity": _jaccard(left_text, right_text)},
                    from_statement=_ref(left_level, 0, left_text),
                    to_statement=_ref(right_level, 0, right_text),
                )
                add_rewrite(
                    _ref(left_level, 0, left_text),
                    f"{left_text} by specifying a distinct causal mechanism.",
                    "Different levels should represent different causal roles, not restate the same phrase.",
                )

    if policy.detect_non_causal:
        if _is_non_causal(purpose):
            add_finding(
                "NON_CAUSAL_STATEMENT",
                "warn",
                "Purpose is phrased as aspiration, not a causal condition; add mechanism/evidence language.",
                {"non_causal_signal": 1.0},
                from_statement=_ref("purpose", 0, purpose),
            )
        for idx, outcome in enumerate(outcomes):
            if _is_non_causal(outcome):
                add_finding(
                    "NON_CAUSAL_STATEMENT",
                    "warn",
                    "Outcome is aspirational but not causally testable; include mechanism or observable condition.",
                    {"non_causal_signal": 1.0},
                    from_statement=_ref("outcome", idx, outcome),
                )

    penalty = 0.0
    for finding in findings:
        if finding.severity == "error":
            penalty += policy.penalty_error
        elif finding.severity == "warn":
            penalty += policy.penalty_warn
        else:
            penalty += policy.penalty_info

    causal_logic = max(0.0, 1.0 - penalty)
    by_link = {
        "outcomes_to_purpose": round(out_to_purpose, 3),
        "purpose_to_goal": round(purpose_to_goal, 3),
        "inputs_to_outcomes": round(in_to_out, 3),
    }

    return CausalLogicOutput(
        findings=findings,
        rewrite_suggestions=rewrites,
        scores=CausalLogicScores(causal_logic=round(causal_logic, 3), by_link=by_link),
    )
