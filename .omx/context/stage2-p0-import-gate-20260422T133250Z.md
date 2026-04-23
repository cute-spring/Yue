task statement
- Stage2 P0 收敛：落地“兼容即默认自动激活（可配置开关）”，保持“路由只看 active skill”语义，保留目录加载可用性，不扩大到后续能力。

desired outcome
- Compatible imports auto-activate by default behind a config switch.
- Runtime routing/projector continues consuming only active skills.
- Directory loading path remains usable without large refactor.
- Docs/tests/code behavior align.

known facts/evidence
- docs/plans 已切到 Stage3/4/5 Lite + P0-first 口径。
- import-gate 核心测试当前可通过（用户提供 45 passed）。
- 当前代码仍偏手动 activate 主路径。

constraints
- TDD first.
- Only touch Stage2 P0 related code/tests/docs.
- No vector recall / rerank / multi-team isolation.

unknowns/open questions
- Auto-activation policy currently represented in which config/service/module.
- Which API/tests encode current manual activation semantics.
- Whether docs already mention config key name.

likely codebase touchpoints
- backend/app/services/*skill*import*
- backend/app/services/*runtime*catalog*
- backend/app/api/*skill_import*
- backend/tests/test_*skill_import*
- docs/plans/skill_import_gate_api_contract_20260421.md
