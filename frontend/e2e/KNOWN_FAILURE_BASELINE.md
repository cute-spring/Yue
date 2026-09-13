# Mocked E2E remediation record

The 2026-09-12 isolated-runtime baseline contained 15 failures. Each has now
been reproduced and verified with an isolated backend port, frontend port, and
temporary `YUE_E2E_DATA_DIR`.

Resolved coverage includes chart replay, slash commands, custom models, MCP
smart paste, multimodal image chat, settings CRUD, and six workspace-grounded
answer scenarios. The relevant combined regression run reports 17 passing
tests; settings CRUD also passes independently.

The complete serial 96-test command exceeds the interactive terminal's
30-second response limit, so it must be run from a persistent CI or local
terminal session for a single-suite gate result.
