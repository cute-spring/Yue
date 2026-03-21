# Nanobot Skill 设计对标与改进计划

日期：2026-03-07

## 目标与范围
- 目标：对比 nanobot 的 skill 设计与实现方式，梳理当前项目技能体系的差距，并提出可落地的改进计划
- 范围：skill 规范、加载与运行时、依赖与可用性、可扩展性与生态、可观测性与测试

## Nanobot Skill 设计要点
- 技能形态：每个技能是目录，核心文件为 SKILL.md，前置 YAML 元信息 + Markdown 指令正文
- 技能来源优先级：workspace 自定义技能优先于内置技能
- 元信息与依赖：通过 metadata 字段携带 nanobot/openclaw 风格 JSON 元数据，支持 requires（bins/env）、install（brew/apt 等）、os 等
- 可用性过滤：加载时根据依赖/环境过滤不可用技能
- 渐进式加载：系统提示词中仅提供技能摘要与路径，需要时由 read_file 读取完整技能
- 常驻技能：支持 always 标记的技能自动进入上下文
- 生态扩展：内置 clawhub 技能，支持搜索与安装公共技能到 workspace

## 当前项目 Skill 体系概览
- 技能文件：系统内置于 `backend/data/skills`，用户级存放在 `~/.yue/skills`。同时支持目录化 `SKILL.md` 与历史单文件 `.md`，YAML frontmatter + System Prompt/Instructions/Examples 等分段
- 解析与校验：SkillLoader 解析 frontmatter 与 Markdown 分段，SkillValidator 校验 entrypoint 对应分段存在
- 运行时适配：MarkdownSkillAdapter 生成 prompt_blocks 与 tool_policy，结合 agent 的 enabled_tools 做交集
- 选择策略：SkillRouter 基于 name/description/capabilities 与请求文本打分；支持 manual/auto 模式与会话绑定
- API 与 UI：提供技能列表与选择 API，前端在 manual 模式下提供技能选择与 Active Skill 状态展示

## 具体差距（现状 -> 影响 -> 增强动作）
1) 技能包结构
   - 现状：nanobot 采用“skill 目录 + SKILL.md + scripts/resources”；当前项目主要是单文件 .md（例如 [ppt-expert.md](file://./backend/data/skills/ppt-expert.md#L1-L27)）
   - 影响：技能一旦需要配套脚本、模板、资产，文件组织会分散，后续复用和迁移成本高
   - 增强动作：引入目录化 skill package（兼容旧 .md），统一为 package manifest + SKILL.md + scripts/resources

2) 依赖与可用性治理
   - 现状：nanobot 有 requires/install/os 元数据并在加载时过滤不可用技能；当前项目 SkillSpec 无这类字段（见 [skill_service.py](file://./backend/app/services/skill_service.py#L15-L33)）
   - 影响：用户会在运行时才踩到“命令不存在/环境变量缺失”，失败点晚且体验差
   - 增强动作：扩展 SkillSpec 字段 + 加载期 availability 判定 + API 返回 missing_requirements

3) 选择前置过滤能力
   - 现状：当前路由主要按可见性与语义分数选 skill（见 [skill_service.py](file://./backend/app/services/skill_service.py#L311-L341)）
   - 影响：有机会选中“语义匹配但不可执行”的技能，导致后续失败回退
   - 增强动作：在 route 前增加“可用性过滤层”，排序维度升级为可用性优先 + 语义分数

4) 上下文注入策略
   - 现状：当前选中 skill 后把 system_prompt/instructions 注入总系统提示词（见 [chat.py](file://./backend/app/api/chat.py#L262-L281)）
   - 影响：多技能并存时提示词膨胀，token 成本与噪声上升，模型稳定性下降
   - 增强动作：改为“摘要常驻 + 正文按需加载”，并支持 always 技能的小块常驻

5) 生态与分发
   - 现状：nanobot 支持 clawhub 搜索/安装技能；当前项目暂无安装/更新/版本仓库流程
   - 影响：技能共享仍依赖手工复制，标准化协作与规模化扩展受限
   - 增强动作：建设内部 skill registry + 安装/更新 API（后续再接 UI/CLI）

6) 可观测与运维
   - 现状：当前有 skill_selected 事件流（见 [chat.py](file://./backend/app/api/chat.py#L289-L290)），但无完整可用性与失败归因指标
   - 影响：难以回答“为何没选中/为何回退/为何执行失败”
   - 增强动作：新增事件与指标：skill_unavailable、skill_rejected_reason、fallback_reason、dependency_miss

## 改进计划（分阶段）

### Phase 1（2 周内）：统一技能包规范与元数据扩展
目标：在保持现有 Markdown 兼容的前提下引入“目录化技能包”与可用性元数据。

- 新增“技能目录 + SKILL.md + scripts/resources”规范
- SkillLoader 兼容读取现有 .md 与新 SKILL.md
- 扩展 SkillSpec 元数据字段：
  - metadata（JSON），requires（bins/env），os，install（brew/apt/pip/conda），homepage，emoji，always
- 输出 API 中增加 availability 与 missing_requirements 字段
- UI 的技能下拉显示“不可用/缺依赖”状态

验收标准
- 旧 .md 技能与新 SKILL.md 技能可同时加载
- /api/skills 返回 availability 与 missing_requirements
- 至少 3 个现有技能完成 package 化迁移试点

交付物
- 规范文档（现有文档中更新，不新增新文档）
- 后端：扩展 SkillSpec 与 SkillLoader/Validator
- 前端：展示可用性与依赖提示

### Phase 2（3-4 周）：运行时渐进式加载与上下文控制
目标：降低 prompt 注入成本，提高多技能扩展能力。

- 系统提示词中仅注入技能摘要（name + description + availability）
- 执行路径中，当选中技能时再按需加载 skill 正文
- 增加 “always skill” 支持，自动加载到上下文
- 对 SkillRouter 增加可用性过滤与优先级排序

验收标准
- 平均系统提示词长度下降 25% 以上
- skill 选择准确率在回归集上不下降
- fallback 因“依赖缺失”触发次数可观测

交付物
- 后端：新增技能摘要与按需加载路径
- 运行时：选择逻辑支持 availability 与 always

## 当前进度（2026-03-08）
- Phase 1：已完成技能包加载兼容、元数据字段扩展、availability 计算、API 暴露、UI 不可用展示
- Phase 1：已完成 3 个现有技能 package 化迁移试点（`ppt-expert`、`excel-metric-explorer`、`pdf-insight-extractor`）
- Phase 2：已完成路由前可用性过滤、摘要注入、always skill 自动注入、选中后按需加载技能正文
- Phase 2：已完成“从消息中自动识别明确技能名称并优先指定”
- Phase 2：已完成“效果验证最小闭环”——`skill_effectiveness` 事件、落库、聚合报表 API、日报脚本
- 测试与验证：新增/更新单测与集成测试；已运行 pytest 子集、unittest 全量、前端 test/build；HTTP 集成测试需 `RUN_HTTP_INTEGRATION_TESTS=1`，TestClient 兼容性问题导致部分 pytest 跳过
- 依赖处理：为后端测试安装 duckdb

## 手工测试用例（详细）

### 测试前置条件
- 启动后端：`cd backend && PYTHONPATH=. python3 app/main.py`（或团队既有启动方式）
- 启动前端：`cd frontend && npm run dev`
- 准备至少 1 个 manual 模式 agent、1 个 auto 模式 agent，并配置可见技能
- 若执行 HTTP 集成链路，设置：`RUN_HTTP_INTEGRATION_TESTS=1`
- 建议清空或记录本次测试前的会话数据，便于核对报表增量

### 用例 1：技能包与旧格式兼容加载
- 用例编号：MAN-SKILL-001
- 目标：验证 `SKILL.md`（package）与历史 `.md` 同时可加载
- 步骤：
  - 打开技能列表页或调用 `GET /api/skills`
  - 确认能看到 package 技能（如 `ppt-expert`）与历史单文件技能（如 `release-test-planner`）
  - 调用 `POST /api/skills/reload` 后再次查询
- 期望结果：
  - 两类技能都存在且可见
  - reload 后数量稳定、无重复、无报错

### 用例 2：可用性与缺依赖展示
- 用例编号：MAN-SKILL-002
- 目标：验证 availability 与 missing_requirements 的可观测性
- 步骤：
  - 调用 `GET /api/skills` 与 `GET /api/skills/summary`
  - 在前端 agent 配置页查看技能下拉状态
  - 人为制造缺依赖条件后重载技能（例如临时移除某依赖）
- 期望结果：
  - API 返回 `availability` 与 `missing_requirements`
  - 前端显示“不可用/缺依赖”状态
  - 不可用技能不会被错误选中为运行技能

### 用例 3：manual 模式显式选技能
- 用例编号：MAN-SKILL-003
- 目标：验证手动选择生效与 Active Skill 展示
- 步骤：
  - 选择 manual agent，并在技能下拉中选择 `ppt-expert`
  - 发送一条与 PPT 生成相关消息
  - 观察聊天区事件与顶部 Active Skill 标签
- 期望结果：
  - SSE 中出现 `skill_selected`，且 name/version 与下拉一致
  - Active Skill 显示为 `ppt-expert@1.0.0`
  - 回答行为符合该技能提示词与工具策略

### 用例 4：消息内明确技能名优先指定
- 用例编号：MAN-SKILL-004
- 目标：验证“消息提及技能名”优先逻辑
- 步骤：
  - 使用 auto 或 manual（未手选技能）agent
  - 发送消息：`请使用 pdf-insight-extractor 提取这份PDF重点`
  - 观察 SSE 事件与响应内容
- 期望结果：
  - 选中 `pdf-insight-extractor`
  - 不出现被其他语义相近技能抢占的情况

### 用例 5：summary-first 与按需加载正文
- 用例编号：MAN-SKILL-005
- 目标：验证未选中时仅摘要注入，选中后加载正文
- 步骤：
  - 发送一条不触发任何技能的通用闲聊消息
  - 发送一条明确触发某技能的任务消息
  - 对比两次返回中的 `skill_effectiveness` 事件字段
- 期望结果：
  - 未触发技能时：`selected_skill=null`，`summary_injected=true`
  - 触发技能时：`selected_skill` 有值，且回答符合技能正文约束
  - `system_prompt_tokens_estimate` 在“未触发技能”场景明显小于“触发技能”

### 用例 6：always skill 自动注入
- 用例编号：MAN-SKILL-006
- 目标：验证 always 技能在上下文中的自动注入能力
- 步骤：
  - 准备一个 `always: true` 且可用的技能并加入可见技能
  - 使用 auto agent 发送普通任务消息与目标任务消息
  - 查看 `skill_effectiveness` 事件中的 `always_injected_count`
- 期望结果：
  - `always_injected_count` 大于 0（满足可见且可用）
  - 在主技能切换时，always 注入仍保持稳定

### 用例 7：技能不可用时回退行为
- 用例编号：MAN-SKILL-007
- 目标：验证不可用技能不会导致崩溃，并且可回退
- 步骤：
  - 让一个可见技能处于不可用状态
  - 发送该技能相关任务
  - 观察选择结果与最终回答
- 期望结果：
  - 不会选择不可用技能执行
  - `skill_effectiveness.reason_code` 为 `no_matching_skill` 或等效回退语义
  - 对话流程正常完成，无 5xx

### 用例 8：技能效果报表 API
- 用例编号：MAN-SKILL-008
- 目标：验证 24h 聚合报表可用
- 步骤：
  - 先执行 5~10 轮包含技能命中与回退的对话
  - 调用 `GET /api/chat/skill-effectiveness/report?hours=24`
  - 调用 `GET /api/chat/skill-effectiveness/report?hours=0`
- 期望结果：
  - 返回包含 `total_runs/skill_hit_rate/fallback_rate/avg_system_prompt_tokens`
  - `reason_distribution` 与 `top_selected_skills` 有合理数据
  - 非法 hours 返回 400（`hours_out_of_range`）

### 用例 9：日报脚本输出
- 用例编号：MAN-SKILL-009
- 目标：验证日报脚本输出结构可直接用于汇报
- 步骤：
  - 执行：`PYTHONPATH=backend python3 backend/scripts/skill_effectiveness_daily_report.py`
  - 校验输出 JSON 字段
- 期望结果：
  - 输出包含 `generated_at` 与 `report`
  - `report` 中包含核心 KPI 与分布字段
  - 当无数据时返回 0 指标而非报错

### 用例 10：端到端回归（前端交互）
- 用例编号：MAN-SKILL-010
- 目标：验证“选择 agent -> 发消息 -> 收事件 -> 展示结果”全链路
- 步骤：
  - 前端选择目标 agent（manual 与 auto 各 1 次）
  - 发送业务消息，观察 UI 中 Active Skill、消息内容、错误提示
  - 打开浏览器 Network，确认 SSE 包含 `chat_id/meta/skill_effectiveness/content`
- 期望结果：
  - UI 展示与 SSE 一致
  - 无明显卡顿或事件乱序导致的展示错误
  - 回退场景仍可正常产出最终答复

### Phase 3（4-6 周）：技能分发与生态扩展（可选）
目标：支持技能安装、共享与版本管理。如果当前不需要分发与生态，可跳过 Phase 3，完成 Phase 2 后直接进入 Phase 4。

- 引入内部“技能仓库/注册表”接口
- 提供 CLI/管理界面：搜索、安装、更新、卸载
- skill 版本管理与兼容性检查（compatibility 字段）

验收标准
- 支持按关键字搜索并安装技能到受控目录
- 支持升级与回滚单个 skill 版本
- compatibility 检查能阻断不兼容安装

交付物
- 管理 API
- 管理 UI 或 CLI
- 版本与兼容性校验策略

### Phase 4（持续迭代）：质量保障与可观测性
目标：提升技能质量与运行可靠性。

- 技能测试框架（静态检查 + 运行时回放）
- 技能使用指标：选择命中率、失败率、回退率、工具调用成功率
- 依赖检查结果持久化并提示修复路径

验收标准
- 每个技能在 CI 至少通过 1 条静态校验 + 1 条运行时回放
- 形成周报指标：命中率、失败率、回退率、依赖缺失率

## 建议优先级（按 ROI）
- P0：Phase 3（分发生态）是否立项决策（当前可选）
- P1：Phase 4 指标面板与周报自动化（基于已落地 `skill_effectiveness`）
- P2：质量门禁深化（更大规模回放集、线上灰度对照）

建议进一步细化为“优先级 + 量化门槛 + 明确 owner”：

| 优先级 | 主题 | 目标周期 | 量化门槛（建议） | Owner | 立项条件 |
|---|---|---|---|---|---|
| P0 | Phase 3 是否立项 | 1 周 | 明确 3 个以上复用场景；安装/升级需求每周 ≥ 5 次 | 产品 + 后端 | 若复用需求不足，则延后 |
| P1 | 指标面板与周报自动化 | 1-2 周 | 周报自动产出成功率 ≥ 99%；核心指标（命中率/回退率/平均提示词长度）可查询 | 后端 + 数据 | 依赖 `skill_effectiveness` 持续落库 |
| P2 | 质量门禁深化 | 2-3 周 | 回放集规模 ≥ 100；灰度流量 ≥ 10%；回退率不劣化 | 后端 + QA | 需要稳定测试样本池 |

建议增加“推进/暂停”决策阈值，避免资源分散：
- 推进 Phase 3：当“技能复用需求”与“跨团队共享诉求”连续两周达标
- 暂缓 Phase 3：当当前瓶颈主要在命中率与回退率，而非分发效率
- 优先 Phase 4：当线上样本增长但指标分析仍依赖人工统计

交付物（建议补齐）
- 测试与质量门禁（回放集、灰度对照、失败归因）
- 监控面板/日志指标（命中率、回退率、提示词长度、依赖缺失率）
- 版本化周报模板（日报聚合 + 周报汇总）

## 关键实施点与代码映射（当前项目）
- Skill 解析与结构：[skill_service.py](file://./backend/app/services/skill_service.py#L48-L362)
- Skill 运行时绑定与效果事件：[chat.py](file://./backend/app/api/chat.py#L208-L410)
- Skill API：[skills.py](file://./backend/app/api/skills.py#L1-L123)
- Agent skill 权限字段：[agent_store.py](file://./backend/app/services/agent_store.py#L16-L41)
- 技能效果报表接口：[chat.py](file://./backend/app/api/chat.py#L794-L802)
- 日报脚本：[skill_effectiveness_daily_report.py](file://./backend/scripts/skill_effectiveness_daily_report.py#L1-L20)
- 示例技能文件（package）：[SKILL.md](file://./backend/data/skills/ppt-expert/SKILL.md#L1-L28)
