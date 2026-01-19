from fastapi import FastAPI
from app.schemas import DraftRequest, DraftResponse, ResumeRequest, ResumeResponse
from app.orchestrator import run_pipeline, resume_with_answers

app = FastAPI(title="LFD-Pro POC")

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