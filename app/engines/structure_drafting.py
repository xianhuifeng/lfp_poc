from openai import OpenAI
import json
from app.prompts import SYSTEM_PROMPT_DRAFT, USER_PROMPT_DRAFT, SYSTEM_PROMPT_REFINE, USER_PROMPT_REFINE
from app.schemas import DraftEngineOutput, DraftLogFrame, ClarificationQuestion

client = OpenAI()

def _clamp_list(x, max_items: int):
    if not isinstance(x, list):
        return x
    return x[:max_items]

def _sanitize_draft_engine_output(data: dict) -> dict:
    # defensive: only touch known fields
    draft = data.get("draft_lfo") or {}
    draft["outcomes"] = _clamp_list(draft.get("outcomes", []), 5)
    draft["inputs"] = _clamp_list(draft.get("inputs", []), 5)
    data["draft_lfo"] = draft

    data["open_questions"] = _clamp_list(data.get("open_questions", []), 5)

    # Also ensure mapping doesn't refer to removed items (optional, but nice)
    mapping = data.get("mapping") or {}
    outcomes_support = mapping.get("outcomes_support") or {}
    inputs_support = mapping.get("inputs_support") or {}

    # keep only keys that still exist after clamping
    kept_outcomes = set(draft.get("outcomes", []))
    kept_inputs = set(draft.get("inputs", []))

    mapping["outcomes_support"] = {k: v for k, v in outcomes_support.items() if k in kept_outcomes}
    mapping["inputs_support"] = {k: v for k, v in inputs_support.items() if k in kept_inputs}
    data["mapping"] = mapping

    return data


def structure_draft(normalized_input: str) -> DraftEngineOutput:
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_DRAFT},
            {"role": "user", "content": USER_PROMPT_DRAFT.format(normalized_input=normalized_input)},
        ],
    )

    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        data = _sanitize_draft_engine_output(data)
        return DraftEngineOutput(**data)
    except Exception as e:
        raise ValueError(f"Invalid LLM JSON: {e}\nRaw output:\n{content}")

def refine_draft(
    normalized_input: str,
    draft_lfo: DraftLogFrame,
    question_set: list[ClarificationQuestion],
    answers: dict[str, str],
) -> DraftEngineOutput:
    draft_json = draft_lfo.model_dump_json(indent=2)
    questions_json = json.dumps([q.model_dump() for q in question_set], indent=2)
    answers_json = json.dumps(answers or {}, indent=2)

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_REFINE},
            {"role": "user", "content": USER_PROMPT_REFINE.format(
                normalized_input=normalized_input,
                draft_json=draft_json,
                questions_json=questions_json,
                answers_json=answers_json,
            )},
        ],
    )

    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        data = _sanitize_draft_engine_output(data)
        return DraftEngineOutput(**data)
    except Exception as e:
        raise ValueError(f"Invalid LLM JSON: {e}\nRaw output:\n{content}")
