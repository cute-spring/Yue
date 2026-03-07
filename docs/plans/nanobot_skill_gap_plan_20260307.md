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
- 技能文件：/backend/data/skills 下的 Markdown 文件，YAML frontmatter + System Prompt/Instructions/Examples 等分段
- 解析与校验：SkillLoader 解析 frontmatter 与 Markdown 分段，SkillValidator 校验 entrypoint 对应分段存在
- 运行时适配：MarkdownSkillAdapter 生成 prompt_blocks 与 tool_policy，结合 agent 的 enabled_tools 做交集
- 选择策略：SkillRouter 基于 name/description/capabilities 与请求文本打分；支持 manual/auto 模式与会话绑定
- API 与 UI：提供技能列表与选择 API，前端在 manual 模式下提供技能选择与 Active Skill 状态展示

## 具体差距（现状 -> 影响 -> 增强动作）
1) 技能包结构
   - 现状：nanobot 采用“skill 目录 + SKILL.md + scripts/resources”；当前项目主要是单文件 .md（例如 [ppt-expert.md](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/ppt-expert.md#L1-L27)）
   - 影响：技能一旦需要配套脚本、模板、资产，文件组织会分散，后续复用和迁移成本高
   - 增强动作：引入目录化 skill package（兼容旧 .md），统一为 package manifest + SKILL.md + scripts/resources

2) 依赖与可用性治理
   - 现状：nanobot 有 requires/install/os 元数据并在加载时过滤不可用技能；当前项目 SkillSpec 无这类字段（见 [skill_service.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L15-L33)）
   - 影响：用户会在运行时才踩到“命令不存在/环境变量缺失”，失败点晚且体验差
   - 增强动作：扩展 SkillSpec 字段 + 加载期 availability 判定 + API 返回 missing_requirements

3) 选择前置过滤能力
   - 现状：当前路由主要按可见性与语义分数选 skill（见 [skill_service.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L311-L341)）
   - 影响：有机会选中“语义匹配但不可执行”的技能，导致后续失败回退
   - 增强动作：在 route 前增加“可用性过滤层”，排序维度升级为可用性优先 + 语义分数

4) 上下文注入策略
   - 现状：当前选中 skill 后把 system_prompt/instructions 注入总系统提示词（见 [chat.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py#L262-L281)）
   - 影响：多技能并存时提示词膨胀，token 成本与噪声上升，模型稳定性下降
   - 增强动作：改为“摘要常驻 + 正文按需加载”，并支持 always 技能的小块常驻

5) 生态与分发
   - 现状：nanobot 支持 clawhub 搜索/安装技能；当前项目暂无安装/更新/版本仓库流程
   - 影响：技能共享仍依赖手工复制，标准化协作与规模化扩展受限
   - 增强动作：建设内部 skill registry + 安装/更新 API（后续再接 UI/CLI）

6) 可观测与运维
   - 现状：当前有 skill_selected 事件流（见 [chat.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py#L289-L290)），但无完整可用性与失败归因指标
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

### Phase 3（4-6 周）：技能分发与生态扩展
目标：支持技能安装、共享与版本管理。

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
- P0：Phase 1 + Phase 2 的前两项（规范、可用性、路由前过滤）
- P1：Phase 2 剩余项（渐进式加载与 always 技能）
- P2：Phase 3（分发生态）
- P3：Phase 4（质量与运营指标深化）

交付物
- 测试与质量门禁
- 监控面板/日志指标

## 关键实施点与代码映射（当前项目）
- Skill 解析与结构：[skill_service.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L48-L362)
- Skill 运行时绑定：[chat.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py#L208-L289)
- Skill API：[skills.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py#L1-L123)
- Agent skill 权限字段：[agent_store.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py#L16-L41)
- 示例技能文件：[ppt-expert.md](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/ppt-expert.md#L1-L27)
