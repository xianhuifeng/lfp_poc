from app.orchestrator import run_amend_draft
from app.schemas import DraftLogFrame


def test_amendment_engine_generates_suggestions():
    lfo = DraftLogFrame(
        goal="Improve software delivery reliability.",
        purpose="Reduce onboarding time for new engineers.",
        outcomes=["New engineers ship code within 6 weeks."],
        inputs=["Create onboarding guide and mentor checklist."],
    )

    out = run_amend_draft(
        raw_text="original brief",
        amendment_text="Timeline changed to 3 weeks. Finance is now an approver.",
        draft_lfo=lfo,
    )

    assert len(out.suggestions) >= 1
    assert all(s.id for s in out.suggestions)
    assert all(s.suggested_text for s in out.suggestions)
