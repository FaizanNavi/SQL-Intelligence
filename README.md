# 🗄️ SQL Intelligence Agent

A natural language → SQL agent built with **LangGraph**, featuring a **self-correction loop** that retries failed queries and a **mandatory safety validator** that blocks all destructive operations.

## 🎯 What This Does
Ask a question in plain English → agent reads the database schema → generates SQL → validates it's safe → executes → explains results in plain English. If the SQL fails, it automatically retries with the error message as context.

**Key engineering features:**
1. **Self-correction loop** — LangGraph conditional edge routes failed SQL back to a fix node (max 2 retries)
2. **Safety validator** — regex + keyword analysis blocks DROP/DELETE/UPDATE before execution
3. **Conversation memory** — last 5 Q&A pairs enable natural follow-ups ("same as before but for Q4")

## 🏗️ Architecture
```
User Question
     │
     ▼
┌──────────────┐
│ Schema Node  │ ← Reads table/column info (cached)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ SQL Generator│ ← LLM generates SELECT query
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Validator   │──→ BLOCKED → Explain (with error)
└──────┬───────┘
       │ (safe)
       ▼
┌──────────────┐     ┌─── fix (if error + retries left)
│  Executor    │ ────►│
└──────┬───────┘     └─── explain (if success or max retries)
       │
       ▼
┌──────────────┐
│  Explainer   │ ← Plain English summary with numbers
└──────────────┘
```

## 🛡️ Safety Features
- **Keyword blocking**: DROP, DELETE, TRUNCATE, UPDATE, INSERT, ALTER, CREATE
- **Injection detection**: statement chaining (`;`), SQL comments (`--`), UNION injection
- **Read-only enforcement**: only SELECT and WITH (CTEs) are allowed
- **Result capping**: max 500 rows returned

## 🛠️ Tech Stack
| Component | Technology |
|-----------|-----------|
| LLM | Groq (Llama 3.3 70B) - free |
| Orchestration | LangGraph state machine |
| Database | SQLite (Chocolate Sales demo data) |
| Framework | FastAPI |
| Safety | Regex-based keyword + pattern analysis |

## 📁 Project Structure
```
P8-SQL-Intelligence/
├── app/
│   ├── __init__.py
│   ├── main.py                    ← FastAPI server
│   ├── agents/
│   │   ├── orchestrator.py        ← LangGraph state machine
│   │   └── sql_agents.py          ← All 6 nodes
│   ├── database/
│   │   └── sqlite_manager.py      ← SQLite + sample data
│   └── utils/
│       ├── config.py              ← Configuration
│       └── safety.py              ← SQL safety checker
├── tests/
│   └── test_sql_agent.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Quick Start
```bash
cd P8-SQL-Intelligence
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY

uvicorn app.main:app --reload --port 8008
```

Then:
```bash
curl -X POST http://localhost:8008/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the total sales by country?"}'
```

## 📐 API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /query | NL question → SQL → results → explanation |
| GET | /schema | View database schema |
| GET | /health | Health check |

## 🧪 Running Tests
```bash
pytest tests/ -v
```

## 📝 Resume Bullet
> "Built SQL Intelligence Agent in LangGraph — LLM translates natural language to SQL queries, a validate node blocks all destructive operations via regex safety checking, a self-correction loop retries failed SQL up to 2 times with the error message as context, and conversation memory enables natural follow-up queries across 5-turn sessions."

## 📄 License
MIT
