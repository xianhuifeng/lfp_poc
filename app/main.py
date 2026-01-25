from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LFD-Pro POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",],
    allow_credentials=True,  # Set to False when using specific origins
    allow_methods=["*"],
    allow_headers=["*"]
)

from app.schemas import DraftRequest, DraftResponse, ResumeRequest, ResumeResponse, RefineRequest, RefineResponse
from app.orchestrator import run_pipeline, resume_with_answers, run_refine


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