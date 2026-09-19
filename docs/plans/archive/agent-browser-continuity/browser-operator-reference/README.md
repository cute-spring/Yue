# browser-operator (reference only — NOT installed)

**ARCHIVED — HISTORICAL, NOT IMPLEMENTED.** These files were recovered verbatim from the deleted
branch `feat/skill-browser-continuity-integration` (tip `b6dc8d5`, 2026-03-29) and are kept as a
design reference for a future skill contract. They are deliberately stored outside
`backend/data/skills/` so the skill runtime does not discover or load them.

- `SKILL.md` — system prompt and constraints for a tool-backed browser operator.
- `manifest.yaml` — action contract for the six tools of that design.

**Why it was not adopted:** the manifest declares tool names (`builtin:browser_open`,
`browser_snapshot`, `browser_click`, `browser_type`, `browser_press`, `browser_screenshot`) that do
not exist on `main`. The shipped browser surface is `browser_read` / `browser_interact` over
`backend/app/services/browser_session_service.py`, with approval envelopes and origin policy instead
of a skill-owned action contract.

If a browser operator skill is ever revived, rewrite the manifest against the current tool names and
approval model rather than reusing this file as-is.
