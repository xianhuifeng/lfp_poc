from openai import OpenAI
from app.schemas import DraftResponse
from app.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

client = OpenAI()

DRAFT_RESPONSE_SCHEMA = DraftResponse.model_json_schema()

def draft_logframe(raw_text: str) -> DraftResponse:
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(raw_text=raw_text)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "DraftResponse",
                "schema": DRAFT_RESPONSE_SCHEMA,
                "strict": True,
            },
        },
        temperature=0,
    )

    data = resp.output_parsed
    if data is None:
        import json
        data = json.loads(resp.output_text)

    return DraftResponse(**data)
