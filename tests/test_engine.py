import os
import pytest
from app.orchestrator import run_pipeline

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
def test_draft_engine_happy_path():
    raw = """
    We want to improve how projects get approved in our organization.Right now, approvals take too long, different teams interpret requirements differently, and many requests get sent back for rework. This causes frustration and delays delivery. Leadership wants faster turnaround without increasing risk or compliance issues.We think the solution might involve clearer criteria, better documentation, training for approvers, and possibly a workflow tool, but we are not sure which changes matter most.Success would mean fewer approval cycles, less rework, and faster time from submission to approval. However, we have not defined exact targets yet. Procurement, Legal, Finance, and IT are all involved.Please help structure this into a logical project design.
    """

    out = run_pipeline(raw)

    assert out.drafting.draft_lfo.goal
    assert out.drafting.draft_lfo.purpose
    assert 0.0 <= out.drafting.confidence <= 1.0
    assert 1 <= len(out.drafting.draft_lfo.outcomes) <= 5
    assert 1 <= len(out.drafting.draft_lfo.inputs) <= 5
