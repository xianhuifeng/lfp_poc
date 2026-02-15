from app.orchestrator import run_amend_draft
from app.schemas import DraftLogFrame
import app.engines.amendment_engine as amendment_engine


def test_amendment_engine_generates_suggestions(monkeypatch):
    lfo = DraftLogFrame(
        goal="Improve software delivery reliability.",
        purpose="Reduce onboarding time for new engineers.",
        outcomes=["New engineers ship code within 6 weeks."],
        inputs=["Create onboarding guide and mentor checklist."],
    )

    amended = DraftLogFrame(
        goal="Improve software delivery reliability.",
        purpose="Reduce onboarding time for new engineers in the first quarter.",
        outcomes=["New engineers ship code within 3 weeks."],
        inputs=["Create onboarding guide and mentor checklist."],
    )

    monkeypatch.setattr(
        amendment_engine,
        "_propose_amended_draft_with_llm",
        lambda payload: amended,
    )

    out = run_amend_draft(
        raw_text="original brief",
        amendment_text="Timeline changed to 3 weeks. Finance is now an approver.",
        draft_lfo=lfo,
    )

    assert len(out.suggestions) >= 1
    assert all(s.id for s in out.suggestions)
    assert all(s.suggested_text for s in out.suggestions)
    assert all(0.0 <= s.confidence <= 1.0 for s in out.suggestions)
    assert any(s.target.level == "outcome" for s in out.suggestions)


def test_amendment_engine_diff_only_returns_changed_fields(monkeypatch):
    lfo = DraftLogFrame(
        goal="Improve software delivery reliability.",
        purpose="Reduce onboarding time for new engineers.",
        outcomes=["New engineers ship code within 6 weeks."],
        inputs=["Create onboarding guide and mentor checklist."],
    )

    # Only purpose changes; everything else stays the same.
    amended = DraftLogFrame(
        goal=lfo.goal,
        purpose="Reduce onboarding time with clearer ownership and weekly reviews.",
        outcomes=lfo.outcomes,
        inputs=lfo.inputs,
    )

    monkeypatch.setattr(
        amendment_engine,
        "_propose_amended_draft_with_llm",
        lambda payload: amended,
    )

    out = run_amend_draft(
        raw_text="original brief",
        amendment_text="There are additional details to consider.",
        draft_lfo=lfo,
    )

    assert out.suggestions
    assert len(out.suggestions) == 1
    assert out.suggestions[0].target.level == "purpose"
