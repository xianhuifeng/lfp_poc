# LogFrame Designer Pro (LFD-Pro) — POC

This repository is a **minimal, engineering-first Proof of Concept** for  
**LogFrame Designer Pro (LFD-Pro) v2**.

The scope of this POC is intentionally narrow and explicit:

> 🎯 **Prove Outcome 1 is feasible**
>
> **Messy human text → structured LogFrame draft**
>
> - No UI  
> - No database  
> - No agents  
> - No memory  
> - Strong schema guarantees  
> - Clear engine boundaries  

If this works, **all six Outcomes in the v2 LogFrame are technically achievable** by layering additional engines.

---

## What This POC Does

Given messy project text, the system produces:

### Engine 2.2 — Input Intake + Preprocessor
- A **normalized version** of the raw input
- A detected **intent**:
  - `create | revise | audit | export | portfolio_check`
- Lightweight **entity hints** (best-effort):
  - goal-like phrases
  - metric keywords
  - organizational terms
- A stable `raw_input_id`

### Engine 2.3 — Structure Drafting Engine
- A **draft Logical Framework**:
  - Goal
  - Purpose
  - Outcomes (1–5)
  - Inputs (1–5)
- A **confidence score** (0–1)
- **Clarifying questions** when information is missing
- A **mapping** that shows how parts of the input support each field

All outputs are:
- Strictly schema-validated (Pydantic)
- Deterministic (temperature = 0)
- Safe to extend with additional engines later

---

## What This POC Explicitly Does *Not* Do

- ❌ No UI
- ❌ No persistence or memory
- ❌ No agent loop or autonomous behavior
- ❌ No portfolio or cross-project reasoning
- ❌ No scoring, audit, or certification logic

Those belong to **later Outcomes**, not this POC.

---

## Tech Stack (Minimal by Design)

### Backend
- Python 3.10+
- FastAPI
- Pydantic v2
- OpenAI API (Chat Completions, JSON-only outputs)
- Uvicorn

### Explicitly NOT Used
- ❌ Database
- ❌ Frontend
- ❌ LangChain / agent frameworks
- ❌ State or memory layers

---

## Project Structure

lfd_poc/
├── app/
│ ├── main.py # FastAPI entrypoint
│ ├── schemas.py # Canonical data contracts (Pydantic)
│ ├── prompts.py # Prompt definitions
│ ├── orchestrator.py # 2.2 → 2.4 pipeline
│ └── engines/
│  ├── intake_preprocess.py # Engine 2.2
│  └── structure_drafting.py# Engine 2.3
│  └── clarification_manager.py# Engine 2.4
├── tests/
│ └── test_pipeline.py # Minimal pipeline tests
├── pyproject.toml
└── README.md

---

## How to Run Locally (Step-by-Step)

### 0. Activate virtual environment (recommended)

```bash
cd lfd_poc
source .venv/bin/activate
pip install --upgrade pip
```

### 1. Prerequisites

Python 3.10 or newer

An OpenAI API key

Check Python version:
python --version

### 2. Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

### 3. Install dependencies

With Poetry:

poetry install
poetry shell

Or manually:

pip install fastapi uvicorn pydantic openai pytest

### 4. Start the API

From the project root:

uvicorn app.main:app --reload


You should see:

Uvicorn running on http://127.0.0.1:8000

### 5. Use the API

Open:

👉 http://127.0.0.1:8000/docs

Expand POST /draft

Paste messy project text

Click Execute

Observe:

preprocess output (2.2)

drafting output (2.3)

### 6. Run tests (optional but recommended)
python -m pytest


Tests will be skipped automatically if OPENAI_API_KEY is not set.

Architecture Overview

This POC follows a layered, engine-oriented architecture.

High-Level Flow
Raw Text
   ↓
Engine 2.2: Intake + Preprocess
   ↓
Engine 2.3: Structure Drafting
   ↓
Schema-Validated Draft LogFrame

## Core Architectural Principles
### 1. Schema-First Design (Non-Negotiable)

Pydantic models define the canonical contract

The LLM must comply or fail

Prevents silent corruption and hallucinated structure

### 2. Engines, Not Agents

Each capability is a pure, stateless engine:

Input → Output

No hidden memory

No implicit orchestration

Independently testable

This POC implements two engines:

Engine 2.2: Intake + Preprocess

Engine 2.3: Structure Drafting

### 3. Orchestration Is Explicit

intent and entities are produced by Engine 2.2

They are not used by Engine 2.3

They are reserved for:

future orchestration decisions

clarification prioritization

downstream engines (audit, measures, assumptions)

This avoids coupling intent detection with semantic reasoning.
