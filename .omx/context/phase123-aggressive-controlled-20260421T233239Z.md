# Ralph Context Snapshot

- task statement: 在可回滚和可验证前提下，并行推进 Phase 1/2/3，至少完成 A/B/C 各 1 个可验证里程碑。
- desired outcome: A(导入闭环与竞态稳态), B(路由管线+可解释字段), C(标准对齐扫描+迁移骨架) 均有 flag 控制且默认关闭。
- known facts/evidence:
  - `backend/app/api/skill_imports.py` 中 upload 导入当前固定返回 `import_unpack_failed`（未闭环）。
  - `backend/app/services/skills/runtime_catalog.py` 与 `backend/app/main.py` 已支持 `import-gate` 模式刷新。
  - `backend/app/services/llm/routing.py` 已有基础 resolve 流程，但未有 recall/rerank explainability 管线字段。
  - 已存在相关 smoke/单测：`test_api_skill_imports.py`, `test_import_gate_lifespan_smoke.py`, `test_llm_routing_unit.py`, `test_chat_stream_runner_unit.py`。
- constraints:
  - 核心逻辑严格 TDD（RED->GREEN->REFACTOR）。
  - 跨阶段改动必须挂 feature flag，默认关闭，需可回滚到 legacy。
  - 关键语义不破坏：import lifecycle、active import runtime、错误码契约。
- unknowns/open questions:
  - upload token 与上传文件的精确映射策略（将通过最小闭环定义为上传目录 token）。
  - routing pipeline 的最小 explainability 字段边界。
- likely codebase touchpoints:
  - A: `backend/app/api/skill_imports.py`, `backend/app/services/skills/*`, `backend/tests/test_api_skill_imports.py`
  - B: `backend/app/services/llm/routing.py`, `backend/app/api/chat_stream_runner.py`, routing tests
  - C: `backend/scripts/*`, 新增 tests
