# Open-Source Skill Preflight And Health Panel Implementation Plan

> 最新交接文档（含当前进度、待办与执行计划）：`docs/superpowers/plans/2026-04-25-open-source-skill-preflight-and-health-panel-handover.md`

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make copied open-source skill packages auto-discoverable at startup, diagnosable in UI, and one-click mountable to default agent.

**Architecture:** Add a startup preflight scanner that reuses current skill parsing/compatibility logic, persist a normalized preflight snapshot, expose it via read APIs, and connect a frontend health panel with mount action. Keep activation and preflight separated so diagnostics remain safe and non-destructive.

**Tech Stack:** FastAPI, Pydantic, existing skill runtime services (`SkillLoader`, `SkillCompatibilityEvaluator`, `SkillImportStore`), React + TypeScript frontend.

---

## Chunk 1: Startup Auto-Discovery And Preflight (Backend)

### Task 1: Add preflight data model and store contract
**Files:**
- Modify: `backend/app/services/skills/import_models.py`
- Modify: `backend/app/services/skills/import_store.py`
- Test: `backend/tests/test_skill_import_store_unit.py`

- [x] **Step 1: Write failing tests for preflight record persistence**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Add `SkillPreflightRecord`/`SkillPreflightSnapshot` model fields**
- [x] **Step 4: Implement store read/write APIs for preflight snapshots**
- [x] **Step 5: Re-run tests and commit**

### Task 2: Build startup preflight scanner
**Files:**
- Create: `backend/app/services/skills/preflight_service.py`
- Modify: `backend/app/services/skills/bootstrap.py`
- Modify: `backend/app/services/skills/__init__.py`
- Test: `backend/tests/test_skill_preflight_service_unit.py`
- Test: `backend/tests/test_skill_runtime_integration.py`

- [x] **Step 1: Write failing unit tests for directory scan and status mapping**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Implement scanner over layered skill directories (`SKILL.md` packages)**
- [x] **Step 4: Classify status to `available|needs_fix|unavailable`**
- [x] **Step 5: Wire scanner into lifespan startup before/after registry load as designed**
- [x] **Step 6: Re-run tests and commit**

## Chunk 2: Preflight Query API And Mount Action (Backend)

### Task 3: Add preflight query endpoints
**Files:**
- Create: `backend/app/api/skill_preflight.py`
- Modify: `backend/app/services/skills/bootstrap.py`
- Test: `backend/tests/test_api_skill_preflight.py`

- [x] **Step 1: Write failing API tests for list/detail/filter**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Implement API routes and response schema**
- [x] **Step 4: Mount router under `/api/skill-preflight`**
- [x] **Step 5: Re-run tests and commit**

### Task 4: Add one-click mount endpoint
**Files:**
- Modify: `backend/app/api/skill_preflight.py`
- Modify: `backend/app/services/skills/import_service.py`
- Test: `backend/tests/test_api_skill_preflight.py`

- [x] **Step 1: Write failing API tests for mount success/idempotency/error**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Reuse import service mount helper to mount by skill ref**
- [x] **Step 4: Return clear mount result codes and messages**
- [x] **Step 5: Re-run tests and commit**

## Chunk 3: Health Panel And UX (Frontend)

### Task 5: Add health panel data layer
**Files:**
- Create: `frontend/src/hooks/useSkillPreflight.ts`
- Create: `frontend/src/types/skillPreflight.ts`
- Test: `frontend/src/hooks/useSkillPreflight.test.ts`

- [x] **Step 1: Write failing tests for fetch/list/filter states**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Implement API client hook and typing**
- [x] **Step 4: Re-run tests and commit**

### Task 6: Add Skill Health Panel UI
**Files:**
- Create: `frontend/src/components/SkillHealthPanel.tsx`
- Modify: `frontend/src/pages/SkillGroups.tsx` (or dedicated skill management page)
- Test: `frontend/src/components/SkillHealthPanel.test.tsx`

- [x] **Step 1: Write failing UI tests for status badges and warning messages**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Render status groups, diagnostics, and actionable hints**
- [x] **Step 4: Add one-click mount button and toast feedback**
- [x] **Step 5: Re-run tests and commit**

### Task 7: Show visibility vs availability explicitly
**Files:**
- Modify: `frontend/src/components/SkillHealthPanel.tsx`
- Test: `frontend/src/components/SkillHealthPanel.test.tsx`

- [x] **Step 1: Write failing UI test for dual-state display**
- [x] **Step 2: Run tests to verify failures**
- [x] **Step 3: Add separate labels (`可用性` and `当前 Agent 可见性`)**
- [x] **Step 4: Re-run tests and commit**

## Chunk 4: Verification And Release Readiness

### Task 8: End-to-end verification and docs
**Files:**
- Modify: `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`
- Create: `docs/guides/developer/SKILL_PREFLIGHT_HEALTH_PANEL_GUIDE.md`

- [x] **Step 1: Add backend verification commands**
- [x] **Step 2: Add frontend verification commands**
- [x] **Step 3: Add copy->restart->diagnose->mount walkthrough**
- [x] **Step 4: Final full test run and commit**
