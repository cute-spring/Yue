# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-02-26

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
