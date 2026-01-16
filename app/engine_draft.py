from openai import OpenAI
from app.schemas import DraftResponse
from app.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

client = OpenAI()

def add_additional_properties_false(schema: dict) -> dict:
    """Recursively add additionalProperties: false and ensure all properties are required for OpenAI compatibility.
    
    Example transformation:
    
    Before (from Pydantic):
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string"}
        },
        "required": ["name", "age"]  # email has default, so not required
    }
    
    After (OpenAI-compatible):
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string"}
        },
        "required": ["name", "age", "email"],  # All properties now required
        "additionalProperties": False  # Added for OpenAI
    }
    """
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
    # By default, OpenAI returns 1 choice (n=1), so choices[0] is safe
    # If n > 1 is specified, this would return the first choice
    if not resp.choices:
        raise ValueError("No choices returned from OpenAI API")
    
    content = resp.choices[0].message.content
    if content is None:
        raise ValueError("No content in response message")
    
    data = json.loads(content)

    return DraftResponse(**data)
