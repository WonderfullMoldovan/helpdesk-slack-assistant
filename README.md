# IT Helpdesk Slack Assistant

AI-powered Slack assistant that automates routine IT support requests for internal employees, with intelligent escalation to human IT engineers when necessary.

**Project type:** Capstone project demonstrating modern AI engineering practices — multi-agent orchestration, human-in-the-loop, observability, and persistent state management.

---

## Architecture Overview

- **Multi-agent system** built on LangGraph with Supervisor + 3 Specialists (Knowledge, Action, Escalation)
- **Hybrid RAG** over knowledge base using pgvector + PostgreSQL full-text search
- **Human-in-the-Loop** via LangGraph interrupt/resume, triggered by low confidence or high-stakes actions
- **Time-triggered reminders** for unanswered escalations
- **Full observability** via Langfuse from day one

See [Solution Design Document](./docs/02-solution-design.md) for complete architecture.

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Docker + Docker Compose
- OpenAI API key
- Slack workspace with bot app configured
- Langfuse account (Cloud or self-hosted)
- `ngrok` (for exposing local server to Slack webhooks)

### Setup

```bash
# 1. Clone and enter project
git clone <repo-url>
cd helpdesk-slack-assistant

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env with your real credentials

# 5. Start infrastructure (Postgres + Redis)
docker compose up -d postgres redis

# 6. Run database migrations (after Alembic setup)
# alembic upgrade head

# 7. Start application
# uvicorn app.main:app --reload --port 8000

# 8. In a separate terminal, expose to internet for Slack
# ngrok http 8000
```

---

## Project Structure

```
helpdesk-slack-assistant/
├── app/                   # Application code
│   ├── api/              # FastAPI routes and Slack webhook handler
│   ├── agents/           # Supervisor, Knowledge, Action, Escalation agents
│   ├── tools/            # Tool implementations for agents
│   ├── rag/              # RAG module (hybrid search)
│   ├── repositories/     # Database access layer
│   ├── observability/    # Langfuse + structured logging
│   └── config/           # Settings, environment variables
├── alembic/              # Database migrations
├── tests/                # Test suite
├── docs/                 # Architecture documentation
│   ├── 01-project-charter.md
│   ├── 02-solution-design.md
│   ├── 03-database-schema.md
│   ├── adr/             # Architecture Decision Records
│   └── defense-cheat-sheet.md
├── pyproject.toml       # Python project configuration
├── docker-compose.yml   # Local development stack
└── README.md
```

---

## Documentation

| Document | Purpose |
|---|---|
| [Project Charter](./docs/01-project-charter.md) | Goals, scope, constraints, success criteria |
| [Solution Design Document](./docs/02-solution-design.md) | Architecture, C4 diagrams, runtime flows |
| [Database Schema](./docs/03-database-schema.md) | Tables, DDL, indexes, LangGraph state |
| [Architecture Decisions](./docs/adr/) | ADRs with alternatives and consequences |

---

## Tech Stack

- **Language:** Python 3.11+
- **Web:** FastAPI + uvicorn
- **Agents:** LangGraph + OpenAI (gpt-4o-mini default, gpt-4o for complex)
- **Database:** PostgreSQL 16 + pgvector
- **Cache:** Redis 7
- **Observability:** Langfuse + structlog
- **Slack:** slack-bolt + slack-sdk
- **Deployment:** Docker Compose (local) → Azure Container Apps (target)

---

## License

Capstone project — internal use only.