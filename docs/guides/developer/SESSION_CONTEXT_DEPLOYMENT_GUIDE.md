# Session Context Dependency Deployment Guide

This guide explains how `Yue` should consume `midterm-session-memory` in three deployment modes.

## 1. Local development with sibling source checkout

This is the fastest developer loop when both repositories live under the same workspace.

```text
ws-ai-recharge-2026/
  ├─ Yue/
  └─ midterm-session-memory/
```

Run:

```bash
./setup.sh
./start.sh
```

If the package is not installed yet, `install_deps.sh` will fall back to the sibling checkout.

## 2. Local or remote install from an internal wheel

This is the recommended deployment shape for machines that should not depend on source checkouts.

Build the wheel in the `midterm-session-memory` repository:

```bash
cd ../midterm-session-memory
./scripts/build_wheel.sh
```

Then install it on the target host:

```bash
pip install /path/to/midterm_session_memory-0.1.0-py3-none-any.whl
```

Or point `Yue` at that artifact directly:

```bash
export YUE_MIDTERM_SESSION_MEMORY_INSTALL_SPEC=/path/to/midterm_session_memory-0.1.0-py3-none-any.whl
./setup.sh
./start.sh
```

## 3. Docker image with both projects baked in

The Docker deployment path currently copies both the `Yue` backend and the `midterm-session-memory` package into the image, then installs the package during build.

This is convenient for self-contained container deployment, but the wheel-based flow is still the cleaner long-term release boundary for non-container hosts.

## What to prefer

- Use the sibling checkout only for local iteration.
- Use the wheel artifact for remote hosts and release environments.
- Use Docker when you want the whole runtime sealed into one image.

## Quick validation

After installation, confirm the dependency is available:

```bash
python3 - <<'PY'
import midterm_memory
print(midterm_memory.__file__)
PY
```

Then run a short session-context smoke test or one of the replay suites.
