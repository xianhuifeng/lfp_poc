import os

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LFD-Pro POC")


def _cors_origins() -> list[str]:
    # Comma-separated list, e.g. "https://your-app.vercel.app,https://other.example.com"
    raw = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.schemas import (
    DraftRequest,
    DraftResponse,
    ResumeRequest,
    ResumeResponse,
    RefineRequest,
    RefineResponse,
    ObjectiveClassifierRequest,
    ObjectiveClassifierResponse,
    CausalLogicRequest,
    CausalLogicResponse,
    AmendDraftRequest,
    AmendDraftResponse,
)
from app.orchestrator import (
    run_pipeline,
    resume_with_answers,
    run_refine,
    run_objective_classifier,
    run_causal_logic,
    run_amend_draft,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/draft", response_model=DraftResponse)
def draft_endpoint(req: DraftRequest):
    return run_pipeline(req.text)

@app.post("/resume", response_model=ResumeResponse)
def resume_endpoint(req: ResumeRequest):
    return resume_with_answers(
        draft_lfo=req.draft_lfo,
        question_set=req.question_set,
        answers=req.answers,
        policy=req.policy,
    )

@app.post("/refine", response_model=RefineResponse)
def refine_endpoint(req: RefineRequest):
    return run_refine(
        raw_text=req.raw_text,
        draft_lfo=req.draft_lfo,
        question_set=req.question_set,
        answers=req.answers,
        policy=req.policy,
    )

@app.post("/classify-objectives", response_model=ObjectiveClassifierResponse)
def classify_objectives_endpoint(req: ObjectiveClassifierRequest):
    classification = run_objective_classifier(
        lfo=req.lfo,
        context=req.context,
        policy=req.policy,
    )
    return ObjectiveClassifierResponse(classification=classification)


@app.post("/causal-logic", response_model=CausalLogicResponse)
def causal_logic_endpoint(req: CausalLogicRequest):
    analysis = run_causal_logic(
        lfo=req.lfo,
        context=req.context,
        policy=req.policy,
    )
    return CausalLogicResponse(analysis=analysis)


@app.post("/amend-draft", response_model=AmendDraftResponse)
def amend_draft_endpoint(req: AmendDraftRequest):
    out = run_amend_draft(
        raw_text=req.raw_text,
        amendment_text=req.amendment_text,
        draft_lfo=req.draft_lfo,
        context=req.context,
        policy=req.policy,
    )
    return AmendDraftResponse(suggestions=out.suggestions)
