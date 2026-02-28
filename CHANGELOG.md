# Changelog

All notable changes to this project will be documented in this file.

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
