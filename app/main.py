from fastapi import FastAPI
from pydantic import BaseModel
from app.engine_draft import draft_logframe
from app.schemas import DraftResponse

app = FastAPI(title="LFD-Pro POC")

class DraftRequest(BaseModel):
    text: str

@app.post("/draft", response_model=DraftResponse)
def draft_endpoint(req: DraftRequest):
    return draft_logframe(req.text)
