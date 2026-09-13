# Mocked E2E remediation record

The 2026-09-12 isolated-runtime baseline contained 15 failures. Each has now
been reproduced and verified with an isolated backend port, frontend port, and
temporary `YUE_E2E_DATA_DIR`.

Resolved coverage includes chart replay, slash commands, custom models, MCP
smart paste, multimodal image chat, settings CRUD, and six workspace-grounded
answer scenarios. The relevant combined regression run reports 17 passing
tests; settings CRUD also passes independently.

The complete serial gate was run on 2026-09-13 using
`npm run test:e2e:mocked -- --reporter=dot`: 96 passed in 2.0 minutes.
