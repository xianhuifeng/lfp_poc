from fastapi import FastAPI
from pydantic import BaseModel
from app.schemas import DraftRequest, DraftResponse
from app.orchestrator import run_pipeline

app = FastAPI(title="LFD-Pro POC")

class DraftRequest(BaseModel):
    text: str

@app.post("/draft", response_model=DraftResponse)
def draft_endpoint(req: DraftRequest):
     return run_pipeline(req.text)
