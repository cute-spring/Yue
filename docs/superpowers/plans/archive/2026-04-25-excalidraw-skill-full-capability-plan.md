# Excalidraw 类 Skill 能力完整化实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `excalidraw-diagram-generator` 及同类“文档+脚本”技能达到可发现、可执行、可观测、可复用、可治理的完整生产能力。

**Architecture:** 采用“Skill 包契约标准化 + Runtime Action 接入 + 资产流水线 + 质量与治理闭环”的分层方案。先把单个技能打通端到端（生成图、图标注入、连线增强、产物回传），再抽象为模板和规范，推广到同类 skills。

**Tech Stack:** Python/FastAPI 技能运行时、Yue Skill Registry/Preflight、Excalidraw JSON、前端 Skill Health 面板、Pytest。

---

## 目录

1. 范围与验收标准  
2. 里程碑总览  
3. Chunk 1：Skill 契约与 Action 化  
4. Chunk 2：图标库资产流水线  
5. Chunk 3：运行时编排与结果回传  
6. Chunk 4：前端能力曝光与可观测性  
7. Chunk 5：测试与发布门禁  
8. Chunk 6：同类 Skills 模板化推广  
9. 风险与回滚策略

## 范围与验收标准

- 范围内：`backend/data/skills/excalidraw-diagram-generator`、`backend/app/services/skills/*`、相关 API/前端展示、测试与文档。
- 范围外：Excalidraw 第三方站点功能改造、非本仓库图形编辑器能力增强。
- 验收标准：用户可通过技能调用直接产出 `.excalidraw` 文件，并可选择图标库注入与自动连线；运行时可报告依赖缺失、执行结果、失败原因；同类 skills 有可复制模板。

## 里程碑总览

- M1（P0）：Skill `manifest.yaml` + `actions` 完成，单技能可执行。
- M2（P0）：图标库资产可导入、可索引、可校验。
- M3（P1）：端到端编排打通（自然语言 -> 文件生成 -> 增强 -> 回传路径）。
- M4（P1）：前端可见性与健康检查完善。
- M5（P1）：测试门禁与发布流程稳定。
- M6（P2）：沉淀“文档+脚本型 Skill”标准模板并推广。

## Chunk 1：Skill 契约与 Action 化

### Task 1.1 定义 manifest 与 resources/actions（P0）

**Files:**
- Create: `backend/data/skills/excalidraw-diagram-generator/manifest.yaml`
- Modify: `backend/data/skills/excalidraw-diagram-generator/SKILL.md`

- [ ] Step 1: 在 `manifest.yaml` 声明 `name/version/description/capabilities/entrypoint`。
- [ ] Step 2: 显式声明 `resources.references`、`resources.scripts`（至少包括 `add-icon-to-diagram.py`、`add-arrow.py`、`split-excalidraw-library.py`）。
- [ ] Step 3: 为核心脚本声明 `actions`（输入参数 schema、输出 schema、安全级别、审批策略）。
- [ ] Step 4: 在 `SKILL.md` 补充 action 调用约定与失败分支（无图标库时降级路径）。
- [ ] Step 5: 本地运行 preflight，确保状态从“可解析”升级为“可执行可治理”。

### Task 1.2 明确能力分级与降级策略（P0）

**Files:**
- Modify: `backend/data/skills/excalidraw-diagram-generator/SKILL.md`

- [ ] Step 1: 定义 L1 基础图（无图标库）、L2 专业图（图标库）、L3 自动增强（连线/标签）三级能力。
- [ ] Step 2: 写清每级触发条件与失败降级策略，避免运行时“静默失败”。
- [ ] Step 3: 增加用户提示模板（缺库、参数错误、文件冲突、编辑后缀冲突）。

## Chunk 2：图标库资产流水线

### Task 2.1 建立标准 libraries 目录与基线资产（P0）

**Files:**
- Create: `backend/data/skills/excalidraw-diagram-generator/libraries/.gitkeep`
- Create: `backend/data/skills/excalidraw-diagram-generator/libraries/README.md`

- [ ] Step 1: 建立 `libraries/<icon-set>/` 标准结构（原始 `.excalidrawlib` + `reference.md` + `icons/`）。
- [ ] Step 2: 约定命名规则与许可证声明字段（来源、版本、许可、更新时间）。
- [ ] Step 3: 提供至少一个可用示例库（例如 AWS 或通用图标集）用于验收。

### Task 2.2 资产预检与可用性校验（P1）

**Files:**
- Modify: `backend/app/services/skills/preflight_service.py`
- Create: `backend/tests/test_skill_preflight_excalidraw_assets_unit.py`

- [ ] Step 1: 在 preflight 增加 Excalidraw 图标资产检查（目录存在、`reference.md` 存在、`icons/` 非空）。
- [ ] Step 2: 输出结构化建议（缺库时给出 `split-excalidraw-library.py` 执行指令）。
- [ ] Step 3: 新增单测覆盖“无库/坏库/可用库”三类场景。

## Chunk 3：运行时编排与结果回传

### Task 3.1 设计 Excalidraw 任务编排器（P1）

**Files:**
- Create: `backend/app/services/skills/excalidraw_orchestrator.py`
- Modify: `backend/app/services/skills/actions.py`
- Modify: `backend/app/services/skills/routing.py`

- [ ] Step 1: 实现编排流程：创建基础图 -> 可选注入图标 -> 可选自动连线 -> 产物保存。
- [ ] Step 2: 统一产物落盘目录与命名规则（防覆盖、可追踪）。
- [ ] Step 3: 返回结构中包含 `output_file_path`、`action_steps`、`warnings`。
- [ ] Step 4: 失败时提供可恢复信息（失败步骤、重试建议、可继续编辑文件）。

### Task 3.2 定义输入输出协议（P1）

**Files:**
- Create: `docs/guides/developer/EXCALIDRAW_SKILL_IO_CONTRACT.md`
- Modify: `backend/data/skills/excalidraw-diagram-generator/SKILL.md`

- [ ] Step 1: 定义自然语言请求到结构化参数映射（图类型、节点、关系、图标需求）。
- [ ] Step 2: 定义输出协议（文件路径、元素统计、打开方式、降级说明）。
- [ ] Step 3: 补充反例和边界条件（元素过多、图标缺失、非法坐标）。

## Chunk 4：前端能力曝光与可观测性

### Task 4.1 Health 面板显示能力等级与阻塞项（P1）

**Files:**
- Modify: `frontend/src/pages/SkillHealth.tsx`
- Modify: `backend/app/api/skill_preflight.py`

- [ ] Step 1: 展示 Excalidraw 专项检查项（图标库可用性、action 可调用性、脚本依赖）。
- [ ] Step 2: 在 UI 标注能力等级（L1/L2/L3）与当前可用等级。
- [ ] Step 3: 对“缺失项”给出一键复制的修复命令与路径。

### Task 4.2 运行日志与事件追踪（P1）

**Files:**
- Modify: `backend/app/services/skills/actions.py`
- Modify: `backend/app/services/skills/import_models.py`

- [ ] Step 1: 记录 action 执行事件（开始/成功/失败/耗时/产物路径）。
- [ ] Step 2: 区分“可重试错误”与“配置错误”。
- [ ] Step 3: 在审计视图保留关键字段，支持排障回放。

## Chunk 5：测试与发布门禁

### Task 5.1 单元与集成测试补齐（P1）

**Files:**
- Create: `backend/tests/test_excalidraw_skill_actions_unit.py`
- Create: `backend/tests/test_excalidraw_skill_e2e_unit.py`

- [ ] Step 1: 覆盖 manifest 解析、action schema 校验、脚本参数透传。
- [ ] Step 2: 覆盖 E2E happy path（无图标与有图标两条主流程）。
- [ ] Step 3: 覆盖失败路径（图标不存在、编辑后缀冲突、JSON 非法）。

### Task 5.2 发布门禁与回归标准（P1）

**Files:**
- Modify: `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`
- Create: `docs/guides/developer/EXCALIDRAW_SKILL_RELEASE_CHECKLIST.md`

- [ ] Step 1: 形成发布前检查清单（preflight 全绿、关键测试通过、样例图可打开）。
- [ ] Step 2: 规定回滚策略（禁用 action、降级为 L1 基础图模式）。
- [ ] Step 3: 建立 smoke 命令清单，纳入 CI 或发布脚本。

## Chunk 6：同类 Skills 模板化推广

### Task 6.1 抽象“文档+脚本型 Skill 模板”（P2）

**Files:**
- Create: `backend/data/skills/_templates/doc-script-skill/manifest.yaml.example`
- Create: `backend/data/skills/_templates/doc-script-skill/SKILL.md.example`
- Create: `docs/guides/developer/DOC_SCRIPT_SKILL_TEMPLATE_GUIDE.md`

- [ ] Step 1: 沉淀统一目录规范（references/scripts/templates/libraries/actions）。
- [ ] Step 2: 提供最小可运行样例与必填字段说明。
- [ ] Step 3: 给出“从只读 skill 升级为 action skill”的迁移步骤。

### Task 6.2 建立推广目标清单（P2）

**Files:**
- Create: `docs/superpowers/plans/skill-template-rollout-targets.md`

- [ ] Step 1: 识别仓内可复用的同类 skills。
- [ ] Step 2: 按收益与复杂度排序，分批迁移。
- [ ] Step 3: 每个迁移目标定义验收标准与负责人。

## 风险与回滚策略

- 风险：第三方图标库版权不清晰。
- 处理：资产目录强制附带 license 来源与使用范围声明。
- 风险：脚本执行引入路径与权限问题。
- 处理：action 审批策略设为受控模式，并限制可写目录。
- 风险：前端显示绿灯但真实执行失败。
- 处理：preflight 与 runtime 执行日志打通，健康态加入“最近执行成功率”。
- 回滚：可快速关闭 Excalidraw actions，仅保留文本指导能力（L1）。

## 完成定义（Definition of Done）

- `excalidraw-diagram-generator` 在运行时可执行核心 actions，且可稳定生成 `.excalidraw` 产物。
- 图标库能力可被 preflight 检测并在 UI 显示状态与修复建议。
- 单测与集成测试覆盖主流程与关键失败路径，发布门禁文档可执行。
- 同类 skill 模板可复用，至少一个额外目标 skill 完成试点迁移。
