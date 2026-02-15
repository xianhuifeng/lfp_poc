from app.orchestrator import run_causal_logic
from app.schemas import DraftLogFrame


def test_causal_logic_happy_path_scores_in_range():
    lfo = DraftLogFrame(
        goal="Improve delivery speed for internal software projects.",
        purpose="Reduce average approval cycle time through clearer criteria and ownership.",
        outcomes=[
            "Average approval turnaround drops from 15 to 7 days.",
            "At least 80% of requests pass first review with complete documentation.",
        ],
        inputs=[
            "Create a standardized approval checklist and decision rubric.",
            "Train approvers and requesters on required evidence and workflow steps.",
        ],
    )

    out = run_causal_logic(lfo=lfo)

    assert 0.0 <= out.scores.causal_logic <= 1.0
    assert "outcomes_to_purpose" in out.scores.by_link
    assert "purpose_to_goal" in out.scores.by_link
    assert "inputs_to_outcomes" in out.scores.by_link


def test_causal_logic_detects_link_gaps():
    lfo = DraftLogFrame(
        goal="Improve national climate resilience.",
        purpose="Increase student coding confidence in one district.",
        outcomes=["Teachers adopt a classroom coding routine weekly."],
        inputs=["Purchase accounting software licenses for finance teams."],
    )

    out = run_causal_logic(lfo=lfo)
    finding_types = {f.type for f in out.findings}

    assert "OUTCOME_TO_PURPOSE_GAP" in finding_types
    assert "INPUT_TO_OUTCOME_GAP" in finding_types


def test_causal_logic_circular_is_advisory_first():
    lfo = DraftLogFrame(
        goal="Reduce onboarding time for new engineers.",
        purpose="Reduce onboarding time for new engineers.",
        outcomes=["New engineers onboard faster."],
        inputs=["Provide onboarding guide and mentor support."],
    )

    out = run_causal_logic(lfo=lfo)
    circular = [f for f in out.findings if f.type == "CIRCULAR_LOGIC"]

    assert circular
    assert all(f.severity == "warn" for f in circular)


def test_causal_logic_detects_non_causal_statement():
    lfo = DraftLogFrame(
        goal="Improve software quality.",
        purpose="We want better team collaboration.",
        outcomes=["Code review quality improves across squads."],
        inputs=["Run weekly peer learning sessions."],
    )

    out = run_causal_logic(lfo=lfo)
    finding_types = {f.type for f in out.findings}

    assert "NON_CAUSAL_STATEMENT" in finding_types
