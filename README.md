

# LogFrame Designer Pro (LFD-Pro) — POC

This repository is a **minimal, engineering-first Proof of Concept** for
**LogFrame Designer Pro (LFD-Pro) v2**.

The scope of this POC is intentionally **narrow, explicit, and testable**:

> 🎯 **Prove Outcome 1 is feasible**
>
> **Messy human text → structured, iteratively refined LogFrame**
>
> * No agents
> * No memory or persistence
> * No portfolio reasoning
> * Strong schema guarantees
> * Clear engine boundaries
> * Human-in-the-loop clarification

If this works, **all six Outcomes in the v2 LogFrame are technically achievable** by layering additional engines.

---

## What This POC Does

Given messy project text, the system assists a user in **creating a solid first-pass LogFrame** through a structured clarification loop.

### Engine 2.2 — Input Intake & Preprocessor

* Normalizes raw input text
* Detects **user intent**:

  * `create | revise | audit | export | portfolio_check`
* Extracts lightweight **entity hints** (best-effort):

  * goal-like phrases
  * metric / measurement keywords
  * organizational terms
* Produces a stable `raw_input_id`

---

### Engine 2.3 — Structure Drafting Engine

* Generates a **first-pass Logical Framework**:

  * Goal
  * Purpose
  * Outcomes (1–5)
  * Inputs (1–5)
* Produces a **confidence score** (0–1) indicating draft completeness
* Generates **open clarification questions** when information is missing
* Provides a **mapping** showing how input text supports each field

All outputs are:

* Strictly schema-validated (Pydantic)
* Deterministic (`temperature = 0`)
* Safe to extend with additional engines

---

### Engine 2.4 — Clarification Manager

* Converts open questions into a **prioritized question set**
* Marks questions as **required** when key details are missing:

  * timeframe / timeline
  * measurement / metrics
  * ownership / responsibility
* Determines the **next system action**:

  * `wait_for_user`
  * `proceed_with_assumptions`

This ensures the system **pauses when critical information is missing** instead of guessing.

---

### Refinement Loop (Human-in-the-Loop)

After the initial draft:

1. The user answers clarification questions
2. The system **re-drafts the LogFrame using those answers**
3. Confidence and remaining questions are updated
4. The loop repeats until the draft is sufficiently clear

This makes the POC a **guided LogFrame assistant**, not a one-shot generator.

---

## Confidence (What It Means)

**Confidence reflects draft completeness**, not idea quality.

It increases when:

* Goal, purpose, outcomes, and inputs are clearly specified
* Required questions are answered
* Measures, timeframe, and ownership are present

It decreases when:

* Required details are missing
* Clarification questions remain open

Confidence **does not judge whether an idea is good or likely to succeed** — only how ready the draft is to move forward.

---

## What This POC Explicitly Does *Not* Do

* ❌ No autonomous agents
* ❌ No memory, replay, or event sourcing
* ❌ No database or persistence
* ❌ No portfolio or cross-initiative reasoning
* ❌ No scoring, certification, or growth tracking

Those belong to **later Outcomes**, not this POC.

---

## Tech Stack (Minimal by Design)

### Backend

* Python 3.10+
* FastAPI
* Pydantic v2 (schema-first)
* OpenAI API (JSON-only completions)
* Uvicorn

### Frontend (Optional, Thin UI)

* Next.js (single-page wizard UI)
* React (no state persistence)
* Used only to:

  * submit text
  * answer clarification questions
  * view draft output

### Explicitly NOT Used

* ❌ Database
* ❌ LangChain / agent frameworks
* ❌ Vector stores
* ❌ Long-term state or memory layers

---

## Project Structure

```
lfd_poc/
├── app/
│  ├── main.py                # FastAPI entrypoint
│  ├── schemas.py             # Canonical data contracts
│  ├── prompts.py             # Draft & refine prompts
│  ├── orchestrator.py        # 2.2 → 2.4 pipeline
│  └── engines/
│     ├── intake_preprocess.py     # Engine 2.2
│     ├── structure_drafting.py    # Engine 2.3 + refine
│     └── clarification_manager.py # Engine 2.4
├── tests/
│  └── test_pipeline.py
├── frontend/                 # Optional Next.js UI
├── pyproject.toml
└── README.md
```

---

## How to Run Locally

### 1. Activate virtual environment (recommended)

```bash
cd lfd_poc
source .venv/bin/activate
pip install --upgrade pip
```

### 2. Prerequisites

* Python 3.10+
* OpenAI API key

```bash
export OPENAI_API_KEY=your_api_key_here
```

### 3. Install dependencies

With Poetry:

```bash
poetry install
poetry shell
```

Or manually:

```bash
pip install fastapi uvicorn pydantic openai pytest
```

---

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

API available at:

👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)
👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 5. Use the API

* `POST /draft` → generate initial draft + questions
* `POST /refine` → apply user answers and improve draft
* `POST /resume` → legacy resume behavior (debug/testing)

---

### 6. Run tests (optional)

```bash
python -m pytest
```

Tests skip automatically if `OPENAI_API_KEY` is not set.

---

## Architecture Overview

### High-Level Flow

```
Raw Text
   ↓
Engine 2.2 — Intake & Preprocess
   ↓
Engine 2.3 — Structure Draft
   ↓
Engine 2.4 — Clarification Manager
   ↓
Human Answers
   ↓
Refinement Loop
```

---

## Core Architectural Principles

### 1. Schema-First Design (Non-Negotiable)

* Pydantic defines the canonical contract
* LLM output is treated as untrusted until validated
* Invalid outputs are sanitized or rejected explicitly

---

### 2. Engines, Not Agents

* Each engine is **pure and stateless**
* Input → Output
* No hidden memory
* Independently testable

This POC implements:

* Engine 2.2 — Intake & Preprocess
* Engine 2.3 — Structure Draft & Refine
* Engine 2.4 — Clarification Manager

---

### 3. Explicit Orchestration

* Intent and entity hints are produced early
* They are **not tightly coupled** to drafting
* Reserved for future orchestration decisions

This avoids premature coupling and keeps the system extensible.
