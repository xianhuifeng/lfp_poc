from app.schemas import DraftResponse
from app.engines.intake_preprocess import preprocess
from app.engines.structure_drafting import structure_draft

def run_pipeline(raw_text: str) -> DraftResponse:
    p = preprocess(raw_text)
    d = structure_draft(p.normalized_input)
    return DraftResponse(preprocess=p, drafting=d)
