import app.engines.objective_classifier as objective_classifier
from app.schemas import DraftLogFrame, ObjectiveClassifierInput


def test_objective_classifier_heuristic_mode_does_not_call_llm(monkeypatch):
    monkeypatch.setenv("OBJECTIVE_CHECK_MODE", "heuristic")

    def _boom(_outcomes):
        raise AssertionError("LLM reviewer should not be called in heuristic mode")

    monkeypatch.setattr(objective_classifier, "_review_outcomes_with_llm", _boom)

    payload = ObjectiveClassifierInput(
        lfo=DraftLogFrame(
            goal="Improve engineering delivery reliability.",
            purpose="Reduce onboarding time for new engineers.",
            outcomes=["New engineers can ship code within 3 weeks."],
            inputs=["Create onboarding guide and mentor checklist."],
        )
    )

    out = objective_classifier.objective_classifier_engine(payload)
    assert out is not None


def test_objective_classifier_llm_mode_can_override_outcome_as_input(monkeypatch):
    monkeypatch.setenv("OBJECTIVE_CHECK_MODE", "llm")

    monkeypatch.setattr(
        objective_classifier,
        "_review_outcomes_with_llm",
        lambda outcomes: {
            0: {
                "is_activity_like": False,
                "is_vague": False,
                "is_measurable": True,
                "confidence": 0.9,
            }
        },
    )

    payload = ObjectiveClassifierInput(
        lfo=DraftLogFrame(
            goal="Improve engineering delivery reliability.",
            purpose="Reduce onboarding time for new engineers.",
            outcomes=["New engineers can ship code within 3 weeks."],
            inputs=["Create onboarding guide and mentor checklist."],
        )
    )

    out = objective_classifier.objective_classifier_engine(payload)
    finding_types = {f.type for f in out.findings}
    assert "OUTCOME_AS_INPUT" not in finding_types
