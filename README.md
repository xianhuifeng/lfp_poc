# LogFrame Designer Pro (LFD‑Pro) — POC

This repository is a **minimal, engineering‑first Proof of Concept** for  
**LogFrame Designer Pro v2**.

The goal of this POC is intentionally narrow:

> 🎯 **Prove Outcome 1 is feasible**
>
> **Messy human text → structured LogFrame draft**
>
> - No UI
> - No database
> - No agents
> - No memory
> - Strong schema guarantees

If this works, everything else can be layered on later.

---

## What This POC Does

Given messy project text, the system produces:

- A **draft Logical Framework**
  - Goal
  - Purpose
  - Outcomes (1–5)
  - Inputs (1–5)
- A **confidence score**
- **Clarifying questions** if information is missing

All outputs are:
- Strictly schema‑validated
- Deterministic (temperature = 0)
- Safe to extend with additional engines later

---

## Tech Stack (Minimal by Design)

### Backend
- Python 3.10+
- FastAPI
- Pydantic v2
- OpenAI API (Responses API + Structured Outputs)
- Uvicorn

### Explicitly NOT Used
- ❌ Database
- ❌ Frontend
- ❌ LangChain / agent frameworks
- ❌ State or memory

---

## Project Structure

```
lfd_poc/
├── app/
│   ├── main.py          # FastAPI entrypoint
│   ├── schemas.py       # Canonical data contracts (Pydantic)
│   ├── prompts.py       # Prompt definitions
│   └── engine_draft.py  # Structure Drafting Engine (Outcome 1)
├── tests/
│   └── test_engine.py   # Minimal pytest coverage
├── pyproject.toml
└── README.md
```

---

## How to Run Locally (Step‑by‑Step)

### 0. 激活虚拟环境（每次开发前）

cd lfd_poc
source .venv/bin/activate
pip install --upgrade pip （强烈建议激活后升级）


### 1. Prerequisites

- Python **3.10 or newer**
- An OpenAI API key

Check Python version:
```bash
python --version
```

---

### 2. Set your OpenAI API key

```bash
export OPENAI_API_KEY=your_api_key_here
```

(Add this to your shell profile if you want it persistent.)

---

### 3. Install dependencies

If you use **Poetry**:
```bash
poetry install
poetry shell
```

Or install manually with pip:
```bash
pip install fastapi uvicorn pydantic openai pytest
```

---

### 4. Start the API

From the project root:

```bash
uvicorn app.main:app --reload
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
```

---

### 5. Use the API

Open your browser:

👉 http://127.0.0.1:8000/docs

- Expand `POST /draft`
- Paste messy project text
- Click **Execute**
- Observe structured output

---

### 6. Run tests (optional but recommended)

```bash
pytest
```

Tests will be skipped automatically if `OPENAI_API_KEY` is not set.

---

## Architecture Overview

This POC follows a **layered, engine‑oriented architecture**.

### High‑Level Flow

```
Raw Text
   ↓
Structure Drafting Engine
   ↓
Schema‑Validated Draft LogFrame
```

---

### Core Architectural Principles

#### 1. Schema‑First Design (Non‑Negotiable)

- Pydantic models define the **canonical contract**
- The LLM must comply or fail
- Prevents silent corruption and hallucinated structure

#### 2. Engines, Not Agents

Each capability is a **pure, stateless engine**:

- Input → Output
- No hidden memory
- No cross‑engine coupling

This POC implements **Engine #1** only.

---

### Engine #1 — Structure Drafting Engine

**Responsibility**
- Convert messy text into a draft LogFrame

**Inputs**
- Raw human text

**Outputs**
- `DraftLogFrame`
- Confidence score
- Clarifying questions

**Failure Mode**
- Invalid output → schema rejection → hard failure (by design)

---

### Planned Engine Expansion (Not Implemented Yet)

```
Engine 1: Structure Drafting        ✅ (this repo)
Engine 2: Objective Classification  ⏳
Engine 3: Causal Logic Validation   ⏳
Engine 4: Indicator Quality Check   ⏳
```

Each engine:
- Reuses the same schemas
- Uses the same FastAPI surface
- Can be independently tested

---

## Why This Architecture Matters

This POC proves:

- The problem is **machine‑assistable**
- The output can be **structurally guaranteed**
- The system can scale **engine‑by‑engine**, not as a monolith

This is not a demo toy.
It is a **credible engineering starting point**.

---

## Next Logical Steps (When Ready)

- Add Objective Classification Engine
- Introduce Canonical LFO v2 schema
- Add UI or chat interface (optional)
- Add persistence only **after** logic is stable

---

## Final Note

> You are not “building an AI system” here.
>
> You are building a **provable, extensible decision‑support engine**.

That distinction matters.
