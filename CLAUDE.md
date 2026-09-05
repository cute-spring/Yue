# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Yue is an AI chat agent platform with a FastAPI/Pydantic-AI backend and SolidJS frontend. It supports multiple LLM providers, MCP (Model Context Protocol) tool integration, skill-based agent runtime, document RAG, and workspace management.

## Commands

### Development
```bash
./setup.sh            # First-time setup: copies .env, installs all deps
./dev.sh              # Foreground dev mode (backend :8003, frontend :3000)
./start.sh            # Background launch with health checks and self-healing
./stop.sh             # Deep-clean process killer
```

### Quality Checks
```bash
./check.sh            # Full stack: pytest + tsc + vitest + playwright
```

### Frontend
```bash
cd frontend
npm run dev           # Vite dev server (port 3000)
npm run build         # tsc --noEmit + vite build
npm run test          # Vitest unit tests
npm run test:e2e      # Playwright E2E tests
```

### Backend
```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -m "not integration"   # Run unit tests only
PYTHONPATH=. pytest                        # Run all tests
```

### Docker
```bash
./deploy_docker.sh    # Build and run Docker container
```

### Environment
- Backend `.env` is at `backend/.env` (copied from `backend/.env.example` by setup.sh)
- On macOS: `DYLD_FALLBACK_LIBRARY_PATH` may need to be set to `/opt/homebrew/lib` for WeasyPrint
- Session context manager dependency: local dev uses a sibling `session-context-manager/src/` directory; production uses a wheel

## Architecture

### Backend (`backend/`)

**Stack:** Python 3.10+, FastAPI, Pydantic-AI, SQLAlchemy + SQLite (sqlite-vec for embeddings), Alembic migrations, MCP SDK

**Route modules** (all under `/api/`):
- `chat.py` — Chat streaming via SSE (primary endpoint)
- `agents.py` — Agent CRUD
- `mcp.py` — MCP configuration management
- `models.py` — LLM provider model listing
- `workspaces.py` — Workspace management (sources, grounded QA)
- `speech.py` — Speech-to-text
- `notebook.py` — Notebook service
- `health.py` — Health check
- `export.py`, `files.py`, `config.py` — Utilities

**Service layer** (`app/services/`):
- `chat_service.py` — Core chat orchestration and streaming
- `chat_prompting*.py` — System prompt building with environment context, history summarization, skill injection
- `chat_retry_service.py` — Tool call mismatch retry logic
- `agent_store.py` — Agent persistence (JSON file)
- `skill_service.py` — Skill management
- `workspace_service.py` — Workspace sources, artifacts
- `doc_retrieval.py` / `vector_search.py` — Document RAG with sqlite-vec
- `model_factory.py` + `llm/` — LLM provider abstraction (OpenAI, Gemini, Ollama, LiteLLM)
- `memory/` — Session context / memory
- `skills/` — Skill runtime (supports "legacy" and "stage-4-lite" modes via `YUE_SKILL_RUNTIME_MODE`)

**MCP layer** (`app/mcp/`):
- `manager.py` — MCP tool lifecycle management
- `registry.py` — Dynamic tool discovery and registration
- `builtin/system.py` — Built-in system tools

**Data layer:**
- SQLAlchemy models in `app/models/`
- Alembic migrations in `app/alembic/versions/`
- Runtime data in `~/.yue/data/` (agents.json, global_config.json, mcp_configs.json, yue.db)

### Frontend (`frontend/`)

**Stack:** SolidJS 1.8, TypeScript, TailwindCSS (emerald design system), Vite, marked + highlight.js + kaTeX + mermaid

**Pages:**
- `Chat.tsx` — Main chat interface with streaming responses
- `Agents.tsx` — Agent management
- `Settings.tsx` — Settings (LLM, MCP, marketplace, smart paste)
- `Notebook.tsx` — Notebook service
- `SkillGroups.tsx` / `SkillHealth.tsx` — Skill management and monitoring

**Component groups:**
- `chat-sidebar/` — Chat list, workspace dock, filters, state management
- `chat-input/` — Multi-modal input, attachments, voice draft
- `message-item/` — Message rendering (assistant body/footer, user content, evidence panels, trace)
- `chat-trace/` — LLM trace inspection UI

**State management:** SolidJS signals (`createSignal`, `createEffect`, `createMemo`) — no external state library.
Key hooks: `useChatState.ts`, `useAgents.ts`, `useLLMProviders.ts`, `useVoiceInput.ts`, `useSpeechSynthesis.ts`.

### Key Architectural Patterns

1. **Chat streaming:** Pydantic-AI agents produce SSE streams; frontend consumes via EventSource
2. **Plugin MCP tools:** Tools are dynamically discovered via MCP registry at startup
3. **Provider abstraction:** LLM providers registered via registry/factory pattern in `app/services/llm/`
4. **Skill runtime:** Pluggable system with bootstrap, lifecycle management, and boundary isolation; two runtime modes
5. **Trace middleware:** Every request gets a trace ID header for distributed debugging
6. **Vite proxy** forwards `/api`, `/files`, `/exports` to backend during development

## Agent skills

### Issue tracker

Issues and specs are managed as local Markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The local tracker uses the default five-role triage vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.
