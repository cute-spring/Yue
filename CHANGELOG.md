# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-02-28

### Added
- **Asynchronous Startup Optimization**:
  - Implemented non-blocking MCP initialization using `asyncio.create_task` in `backend/app/main.py` for immediate API readiness.
  - Added `is_initializing` state to `McpManager` in `backend/app/mcp/manager.py` for background status tracking.
  - Enhanced `/api/health` in `backend/app/api/health.py` to return `status: "initializing"` during MCP startup, improving system observability.
- **Production-grade Model Availability Check**:
  - Implemented parallel initialization for MCP servers in `backend/app/mcp/manager.py` for faster startup.
  - Added Pydantic-based configuration validation and semantic version compatibility checks for MCP servers.
  - Implemented exponential backoff retry logic for resilient MCP server reconnections.
- **Global Health Monitoring System**:
  - Created a singleton `HealthMonitor` in `backend/app/services/health_monitor.py` for background periodic checks of MCP and LLM providers.
  - Added a comprehensive `/api/health` endpoint for real-time system status observability.
  - Implemented deep connectivity checks for LLM providers (network-level verification).
- **Enhanced LLM Provider Management**:
  - Improved configuration security by detecting placeholder API keys in `openai.py`.
  - Added smart model filtering in `factory.py` to only show available models from healthy providers in the UI.

### Fixed
- **API Stability**:
  - Resolved 500 Internal Server Error and JSON parsing issues by disabling unstable test MCP servers in `~/.yue/data/mcp_configs.json`.
  - Fixed `NameError: name 'asyncio' is not defined` in `backend/app/main.py` lifespan hook.
  - Resolved import conflicts in `backend/app/api/models.py` by unifying LLM provider imports.
- **Uvicorn Lifecycle**:
  - Disabled auto-reload mode in `backend/app/main.py` to prevent incomplete responses during high-frequency configuration changes.

### Changed
- **E2E Testing Stability**:
  - Fixed multiple Playwright E2E tests (`comprehensive-workflow.spec.ts`, `verify-stop.spec.ts`, `custom-models.spec.ts`) to align with UI changes and improve reliability.
  - Updated `global_config.json` to include the latest enabled models and configuration schema.

## [Unreleased] - 2026-02-27

### Added
- **Adapter Pattern for Reasoning Chains**: Implemented `getAdaptedThought` in `frontend/src/utils/thoughtParser.ts` to unify structured thought fields and embedded `<think>` tags.
- **Visual Intelligence Panel**: Added a token distribution donut chart in `IntelligencePanel.tsx` for real-time monitoring of Prompt vs. Completion tokens.
- **Structured Thought UI**: Added a `STRUCTURED` label in `MessageItem.tsx` to distinguish model-native reasoning from parsed content.

### Changed
- **Optimized Thought Parsing**: Refined `MessageItem.tsx` to prioritize backend-provided `thought` fields over content parsing.
- **Enhanced Streaming UI**: Improved the "Thinking" state visualization with smoother animations and progress indicators.
- **Intelligence Dashboard**: Upgraded the `stats` panel to display TPS, total tokens, and finish reasons with a polished design.

## [0.2.0] - 2026-02-26

### Added
- Created `pyproject.toml` in `backend/` to replace `requirements.txt`, following PEP 621.
- Added `uv.lock` for deterministic dependency resolution in the backend.
- Added `README.md` to `backend/` for package metadata compliance.
- Added `dependency-groups` for development tools (pytest, etc.) in `pyproject.toml`.

### Changed
- Migrated backend dependency management from `pip` to `uv`.
- Updated `install_deps.sh` to prioritize `uv sync` for backend dependencies while maintaining backward compatibility.
- Updated `dev.sh` to use `uv run python -m app.main` for the backend, simplifying environment management.
- Updated `start.sh` to use `uv run` for background process execution.
- Updated `docs/ROADMAP.md` with the latest Phase 3 status snapshot.

### Removed
- Deleted `backend/requirements.txt` in favor of `pyproject.toml`.
