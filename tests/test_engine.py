import os
import pytest
from app.engine_draft import draft_logframe

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
def test_draft_engine_happy_path():
    raw = """
    We want a one-day STEM event for high school students.
    Scientists will host hands-on activities.
    We need a schedule, mentors, and registration.
    """

    out = draft_logframe(raw)

    assert out.draft_lfo.goal
    assert out.draft_lfo.purpose
    assert 0.0 <= out.confidence <= 1.0
    assert 1 <= len(out.draft_lfo.outcomes) <= 5
    assert 1 <= len(out.draft_lfo.inputs) <= 5
