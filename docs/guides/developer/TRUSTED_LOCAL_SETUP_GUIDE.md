# Trusted Local Setup Guide

## Purpose

This guide explains the Trusted Local Setup workflow for skill packages that declare an `install.setup` contract. It covers:

- Manifest format and runtime support
- The Trust → Setup lifecycle
- Security policy gates
- API endpoints and Health UI integration
- Audit observability

## Concept

Trusted Local Setup lets users prepare copied skill packages for use through an
explicit, auditable trust-and-execute flow. Setup runs inside an isolated
per-skill environment under the skill root. No arbitrary third-party scripts
execute at chat time — only manifest-declared setup commands after explicit user
trust.

## Manifest Contract

A skill package declares setup intent in `manifest.yaml`:

```yaml
format_version: 1
name: my-skill
version: 1.0.0
description: A skill with Python dependencies
capabilities: ["analysis"]
entrypoint: system_prompt
install:
  setup:
    runtime: python
    commands:
      - python -m venv .yue/python/venv
      - .yue/python/venv/bin/pip install -r requirements.txt
```

Or for Node:

```yaml
install:
  setup:
    runtime: node
    commands:
      - npm install --prefix .yue/node
```

### Constraints

- `runtime` must be `python` or `node`
- `commands` must be a non-empty list of plain strings
- No shell metacharacters: `;`, `&&`, `||`, `|`, `` ` ``, `$(` are rejected
- No inline code execution: `-c`, `-e` flags are blocked
- No global installation: `-g`, `--global`, `--user` flags are rejected

## Supported Runtimes

### Python

Allowed executables: `python`, `pip`, `uv`.

Allowed command patterns:

| Pattern | Purpose |
|---------|---------|
| `python -m venv .yue/python/venv` | Create isolated venv |
| `.yue/python/venv/bin/pip install -r requirements.txt` | Install dependencies into venv |
| `.yue/python/venv/bin/pip install <package>` | Install specific packages |
| `.yue/python/venv/bin/python -m pip install ...` | Pip via Python module |

All pip operations must use the venv-local `pip` binary. System `pip` is rejected.

### Node

Allowed executables: `npm`, `pnpm`, `yarn`.

Allowed command patterns:

| Manager | Flag | Example |
|---------|------|---------|
| npm | `--prefix` | `npm install --prefix .yue/node` |
| pnpm | `--dir` | `pnpm install --dir .yue/node` |
| yarn | `--cwd` | `yarn install --cwd .yue/node` |

The target path must resolve to `.yue/node` under the skill root. Any other path
or missing flag is rejected. Only `install` is allowed (no `run`, `build`, etc.).

## Isolated Environment

Setup always executes in a per-skill isolated directory:

| Runtime | Default Path |
|---------|-------------|
| Python | `<skill_root>/.yue/python/venv` |
| Node | `<skill_root>/.yue/node` |

These directories are created automatically before command execution. The skill
root is computed from `source_path` on the preflight record.

Policy gates enforced at execution time:

- **Deny patterns**: Shell metacharacters, dangerous binaries
- **Allow patterns** (if configured): Only matched commands pass
- **Workspace restriction** (if enabled): `cwd` must be within project root
- **Path escape rejection**: `--prefix`, `--dir`, `--cwd` targets must stay inside skill root

## Trust & Setup Lifecycle

```
untrusted  ──[Trust]──▶  trusted  ──[Setup]──▶  succeeded
    │                        │                      │
    │                        │                      │
    └──[Package changed]────  └──[Package changed]──▶  untrusted (requires rescan)
                             │
                             └──[Setup failed]──▶  failed (Retry Setup)
```

### Step 1: Preflight

At startup, the runtime scans skill directories and builds preflight records.
Skills with a valid `install.setup` block get:

- `setup_capable: true`
- `setup_required: true`
- `setup_status: "available"` (if trusted) or `"not_needed"` (if not)
- `trust_status: "untrusted"`

### Step 2: Trust

The user explicitly approves a skill for setup via the SkillHealth UI or API.
A package fingerprint (SHA-256 of all files excluding `.yue/`) is computed and
stored. If the package contents change after trust, the trust is revoked and a
rescan is required.

### Step 3: Setup

Setup runs each command in order. Each command's execution details (timing,
exit code, stdout/stderr sizes) are recorded as audit entries. If any command
fails, setup stops and the failure is recorded.

### Step 4: Retry

If setup fails, the user can fix the issues and retry. Trust is preserved
unless the package fingerprint has changed.

## Fingerprint Binding

Trust and setup state are bound to a cryptographic fingerprint of the package
contents. The fingerprint is computed when:

- Preflight scans the package
- Trust is approved
- Setup is about to start (`_ensure_trusted_fingerprint`)

If the fingerprint changes at any gate, trust is revoked and the user must
rescan and retrust before setup can proceed.

Files under `.yue/` are excluded from the fingerprint to avoid invalidating
state when the isolated environment is populated.

## API Endpoints

### Trust a skill

```
POST /api/skill-preflight/{skill_ref}/trust
```

- Requires: `setup_capable: true`, fingerprint unchanged since preflight
- On success: returns updated record with `trust_status: "trusted"`

### Run setup

```
POST /api/skill-preflight/{skill_ref}/setup
```

- Requires: `trust_status: "trusted"`, `setup_capable: true`
- Runs each command in order, records audit entries
- Response includes `setup_audit_summary`

### Get setup state

```
GET /api/skill-preflight/{skill_ref}/setup
```

- Returns current `setup_status`, `setup_last_error`, `setup_audit_entries`

### Error payloads

All endpoints return structured errors:

```json
{
  "detail": {
    "code": "skill_setup_requires_trust",
    "message": "Trust this skill before running setup.",
    "next_action": "Use the Trust & Setup button in Skill Health."
  }
}
```

Common error codes:

| Code | Meaning |
|------|---------|
| `skill_setup_requires_trust` | Skill is not trusted |
| `skill_setup_not_supported` | `setup_capable` is false |
| `skill_setup_requires_rescan` | Package fingerprint changed |
| `skill_setup_contract_invalid` | Manifest has no commands |

## Setup Audit Observability

Each setup run produces per-command audit entries in the preflight record:

```json
{
  "setup_audit_entries": [
    {
      "command": "python -m venv .yue/python/venv",
      "argv": ["python", "-m", "venv", ".yue/python/venv"],
      "cwd": "/path/to/skill",
      "exit_code": 0,
      "stdout_size": 1024,
      "stderr_size": 0,
      "duration_ms": 2450,
      "started_at": "2026-05-09T12:00:00Z",
      "finished_at": "2026-05-09T12:00:02Z"
    }
  ],
  "setup_audit_summary": {
    "total": 1,
    "succeeded": 1,
    "failed": 0,
    "total_duration_ms": 2450
  }
}
```

Audit entries are reset on each rerun and are backward-compatible with existing
preflight records (missing field defaults to empty list).

The API serialization layer exposes `setup_audit_summary` so the Health UI can
render a quick summary without parsing all entries.

## SkillHealth UI

The `/skill-health` page surfaces the Trust & Setup workflow:

### Setup action states

| Condition | Button Label | Disabled |
|-----------|-------------|----------|
| `setup_capable: false` | Setup Unsupported | Yes |
| `trust_status: "untrusted"` | Trust & Setup | No |
| `trust_status: "trusted"` + `setup_status: "failed"` | Retry Setup | No |
| `trust_status: "trusted"` + `setup_status: "succeeded"` | Setup Complete | Yes |
| `setup_status: "running"` | Running Setup | Yes |

### Information displayed

- Trusted setup support message (runtime list)
- Trust status (Yes / No)
- Setup status message (actionable backend copy)
- Last failure message (on failure)
- Setup next action hint
- Setup audit summary (when available)

## Troubleshooting

### "install.setup.runtime must be one of: python, node"

The manifest declares an unsupported runtime (e.g., `bash`). Only `python` and
`node` are supported in Phase 1.

### "setup command rejected by Phase 1 policy"

The command violates one or more security gates:

- Contains shell metacharacters or inline code
- References a path outside the skill root
- Uses a disallowed executable or flag
- Missing required flag for the package manager (`--prefix`, `--dir`, `--cwd`)

### "Package contents changed since trust approval"

The skill package files have changed. Rescan preflight and retrust before
retrying setup.

### "Package contents changed since preflight"

The skill package changed between preflight and trust. Run rescan to refresh
the fingerprint, then trust again.

## Package Manager Quick Reference

### npm

```yaml
install:
  setup:
    runtime: node
    commands:
      - npm install --prefix .yue/node
```

### pnpm

```yaml
install:
  setup:
    runtime: node
    commands:
      - pnpm install --dir .yue/node
```

### yarn

```yaml
install:
  setup:
    runtime: node
    commands:
      - yarn install --cwd .yue/node
```

### Python (venv + pip)

```yaml
install:
  setup:
    runtime: python
    commands:
      - python -m venv .yue/python/venv
      - .yue/python/venv/bin/pip install -r requirements.txt
```

### Python (multiple packages)

```yaml
install:
  setup:
    runtime: python
    commands:
      - python -m venv .yue/python/venv
      - .yue/python/venv/bin/pip install numpy pandas
```
