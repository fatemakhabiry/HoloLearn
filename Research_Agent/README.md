# Research Agent — Planner + Executor
**General Domain | LangGraph | Python 3.10+**

Part of the **HoloLearn-AI** project.

---

## Quick Start

### 1. Add your API keys

```
HoloLearn-AI/
└── Research_Agent/
    └── .env          ← create this file
```

Copy `.env.example` → `.env` and fill in:

```env
GROQ_API_KEY=gsk_...       # https://console.groq.com  (free)
TAVILY_API_KEY=tvly-...    # https://app.tavily.com    (free)
MODEL_FLASH=llama-3.3-70b-versatile
```

### 2. Install dependencies

```powershell
# From HoloLearn-AI root (your existing venv is fine)
pip install -r Research_Agent/requirements.txt
```

### 3. Run

```powershell
# From HoloLearn-AI root:
python Research_Agent/main.py

# With a question directly:
python Research_Agent/main.py --question "What is quantum computing?"

# With JSON output:
python Research_Agent/main.py --question "How does mRNA work?" --json

# From inside Research_Agent/:
python main.py
```

---

## How it works

```
Question
   │
   ▼
[Planner]  — one LLM call → InvestigationPlan (6-10 sub-questions)
   │
   ▼
[Executor] — asyncio.gather → all independent steps run in parallel
   │              ↑ loops back if more steps remain
   ▼
Findings printed to terminal
```

---

## Project Structure

```
Research_Agent/
├── main.py                        # Entry point
├── .env                           # Your keys (never commit this)
├── .env.example                   # Template
├── requirements.txt
├── README.md
│
├── graph/
│   ├── state.py                   # AgentState TypedDict
│   └── research_graph.py          # LangGraph StateGraph
│
├── agent/
│   ├── planner.py                 # Planner node
│   └── executor.py                # Executor node (parallel)
│
├── tools/
│   └── __init__.py                # web_search + wikipedia
│
├── prompts/
│   ├── __init__.py                # Prompt builders
│   └── personas/
│       └── general.py             # General domain Persona
│
├── schemas/
│   └── __init__.py                # Pydantic models
│
├── llm/
│   └── __init__.py                # Groq client + role aliases
│
├── utils/
│   └── __init__.py                # print_plan(), print_findings()
│
└── tests/
    └── test_agent.py
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `KeyError: 'GROQ_API_KEY'` | Create `Research_Agent/.env` with your key |
| `ModuleNotFoundError: groq` | `pip install -r Research_Agent/requirements.txt` |
| `ModuleNotFoundError: langgraph` | Same as above |
| `tavily` errors | Add `TAVILY_API_KEY` to `.env` |
