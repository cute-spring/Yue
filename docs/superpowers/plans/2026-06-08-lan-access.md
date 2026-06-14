# LAN Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Yue development and startup flows reachable from other devices on the local network while keeping an explicit localhost-only mode available.

**Architecture:** The backend will read an explicit host/port from environment variables and default to `0.0.0.0` for LAN-friendly startup. The frontend Vite dev server will likewise bind to `0.0.0.0` by default, while the startup scripts will print the correct local and LAN URLs and keep health checks pointed at the local machine.

**Tech Stack:** Bash startup scripts, FastAPI/Uvicorn, Vite, environment variables.

---

### Task 1: Backend host binding

**Files:**
- Modify: `backend/app/main.py:195-202`

- [ ] **Step 1: Verify the file compiles after the host/port change**

Run: `python -m py_compile backend/app/main.py`
Expected: no syntax errors.

- [ ] **Step 2: Confirm the backend now reads `YUE_BACKEND_HOST` and `YUE_BACKEND_PORT`**

Run: `rg -n "YUE_BACKEND_HOST|YUE_BACKEND_PORT|uvicorn.run" backend/app/main.py`
Expected: the `__main__` block uses environment-driven host and port values.

### Task 2: Frontend dev server binding

**Files:**
- Modify: `frontend/vite.config.ts:1-28`

- [ ] **Step 1: Verify the frontend still builds with the new server config**

Run: `cd frontend && npm run build`
Expected: build succeeds and Vite accepts the updated server settings.

- [ ] **Step 2: Confirm the frontend reads `YUE_FRONTEND_HOST` and `YUE_FRONTEND_PORT`**

Run: `rg -n "YUE_FRONTEND_HOST|YUE_FRONTEND_PORT|server:" frontend/vite.config.ts`
Expected: the dev server host and port are configurable from the environment.

### Task 3: Startup script and documentation updates

**Files:**
- Modify: `start.sh:1-252`
- Modify: `dev.sh:1-57`

- [ ] **Step 1: Verify the startup scripts remain syntactically valid**

Run: `bash -n start.sh && bash -n dev.sh`
Expected: both scripts parse cleanly.

- [ ] **Step 2: Verify the scripts export LAN-friendly defaults and print LAN URLs**

Run: `rg -n "YUE_BACKEND_HOST|YUE_FRONTEND_HOST|LAN access|Local access" start.sh dev.sh`
Expected: both scripts default to `0.0.0.0` and show the LAN IP in their output.
