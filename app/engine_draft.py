from openai import OpenAI
from app.schemas import DraftResponse
from app.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

client = OpenAI()

def add_additional_properties_false(schema: dict) -> dict:
    """Recursively add additionalProperties: false and ensure all properties are required for OpenAI compatibility."""
    if isinstance(schema, dict):
        # If it's an object type, add additionalProperties: false
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            # OpenAI requires all properties to be in the required array
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())
        # Recursively process all values (including properties, items, $defs, etc.)
        for key, value in schema.items():
            if isinstance(value, (dict, list)):
                add_additional_properties_false(value)
    elif isinstance(schema, list):
        # Process each item in the list
        for item in schema:
            if isinstance(item, (dict, list)):
                add_additional_properties_false(item)
    return schema

DRAFT_RESPONSE_SCHEMA = add_additional_properties_false(DraftResponse.model_json_schema())

def draft_logframe(raw_text: str) -> DraftResponse:
    print(client)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
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

    import json
    content = resp.choices[0].message.content
    data = json.loads(content)

    return DraftResponse(**data)
