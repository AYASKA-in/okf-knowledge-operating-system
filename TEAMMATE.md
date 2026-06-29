# OKF Knowledge Operating System

## Goal

Build a knowledge operating system that stores, links, searches, and serves enterprise knowledge using **OKF (Open Knowledge Format)** — plain markdown files with YAML frontmatter. The system provides a FastAPI REST API for ingesting documents, managing knowledge concepts, searching across them, and chatting with an LLM-powered agent.

**Spec constraints:**
- `type` required in YAML frontmatter; no `[[wiki links]]`; standard `[markdown](./links.md)`
- Reserved files: `index.md` and `log.md` per workspace
- Backend-first: all backend phases before any frontend work

## Architecture

```
app/
  api/        # FastAPI route handlers (auth, knowledge, search, chat, ingest, export, edges, admin)
  agents/     # ChatAgent, IngestorAgent, StructurerAgent, LinkerAgent
  auth/       # JWT + bcrypt password hashing
  models/     # SQLAlchemy DB models + Pydantic OKF models + API schemas
  storage/    # BundleManager (filesystem read/write of OKF markdown)
  llm/        # VertexAIClient (wraps Google Vertex AI; falls back rule-based without GCP)
  config.py   # Pydantic-settings config
  main.py     # FastAPI app entrypoint
  database.py # AsyncSession factory
tests/        # pytest suite (117 tests)
```

**Data flow:** Ingest → Structurer → Linker → filesystem (`BundleManager`) + PostgreSQL (`Node`/`Edge` tables). Search uses PostgreSQL FTS with fallback to SQLite-compatible LIKE. Chat uses filesystem concepts with rule-based scoring.

## What's Done

### API Endpoints (37 routes)

| Group | Endpoints |
|---|---|
| Auth | `POST /v1/auth/token` (login), `POST /v1/auth/refresh`, `GET /v1/auth/me` |
| Knowledge | CRUD: `GET/POST /v1/knowledge`, `GET/PUT/DELETE /v1/knowledge/{id}`, `POST /v1/knowledge/{id}/links` |
| Search | `POST /v1/search` — full-text search with `type_filter`, `tag`, `offset`/`limit`, `X-Total-Count` header, edge-count ranking boost + fallback path |
| Edges | `POST /v1/edges`, `GET /v1/knowledge/{id}/edges`, `DELETE /v1/edges/{id}` |
| Admin | Workspace CRUD (5 endpoints), User CRUD (5 endpoints), `GET /v1/admin/audit-logs` |
| Chat | `POST /v1/chat` — context retrieval + LLM answer with citations |
| Ingest | `POST /v1/ingest` — splits markdown into sections, structures OKF concepts, links related concepts |
| Export | `POST /v1/export` — zips workspace bundle |

### Key Features

- **Edge knowledge graph** — `Edge` DB table with types: `references`, `depends_on`, `parent_of`, `related_to`. Created automatically by LinkerAgent during ingest and create-concept. Inbound edge count boosts search ranking.
- **LinkerAgent** — keyword + embedding-based relevance scoring between concepts; appends "## See Also" markdown links and creates `Edge` DB rows.
- **Search ranking boost** — `rank = FTS_rank + inbound_edge_count * 0.1`; fallback sorts by `edge_count DESC, updated_at DESC`.
- **X-Total-Count header** on list/search endpoints for pagination.
- **Vertex AI integration** — gated via `GCP_PROJECT_ID` env var; zero-config fallback without it.

### Infrastructure

- **Docker Compose** — PostgreSQL 16 + API service with healthcheck
- **Dockerfile** — python:3.12-slim, uvicorn
- **Alembic** — 2 migration versions (initial schema + indexes/constraints)
- **SQLite in-memory** for CI tests; PostgreSQL for production
- **Test count:** 117 passing + 4 skipped (Vertex AI gated)

### Notable Fixes

- `OKFFrontmatter.timestamp` coerces `datetime` → ISO string (YAML parse bug)
- `StringArray.cache_ok = True` suppresses SAWarning
- Search count query restructured to avoid cartesian product warning
- `Edge`/`or_` imports added to `knowledge.py` (missing import bug)

## Running

```powershell
# Install
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Run tests
.\.venv\Scripts\python.exe -m pytest tests/ -v

# Run API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Docker (full stack with PostgreSQL)
docker compose up -d
```

Python 3.10.11 at `D:\python.exe`; venv at `.\.venv\`.

## Config

Key `settings` (from `app/config.py`):

| Env Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///:memory:` | DB connection |
| `OKF_BUNDLE_ROOT` | `./okf_bundles` | Filesystem root for OKF markdown |
| `JWT_SECRET` | `change-me` | JWT signing key |
| `GCP_PROJECT_ID` | `""` | Vertex AI project (empty = fallback mode) |
| `CHAT_MODEL` | `gemini-2.0-flash-001` | LLM model for chat |

## Team Member Onboarding

1. Read `app/models/okf.py` — understand the OKFConcept/OKFFrontmatter models
2. Read `app/storage/bundle.py` — BundleManager (filesystem operations)
3. Read `app/api/knowledge.py` — core CRUD pattern (reference for all endpoints)
4. Read `app/agents/linker.py` — relevance scoring and edge creation
5. Run the tests: `pytest tests/ -v`
6. Review `tests/test_api.py` for integration test patterns
