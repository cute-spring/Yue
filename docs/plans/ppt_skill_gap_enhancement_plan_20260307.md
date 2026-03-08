# PPT Skill Gap 逐步增强设计与测试计划

## 背景与现状
- 当前 skill 以 `ppt-expert.md` 为核心，主要负责从 outline 到 slide JSON 并调用 `generate_pptx`（见 [ppt-expert.md:L1-L27](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/ppt-expert.md#L1-L27)）。
- 生成能力由 `GeneratePptxTool` 与 `generate_pptx.py` 驱动，支持多种 slide type 与默认 theme（见 [ppt.py:L1-L35](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/ppt.py#L1-L35)，[generate_pptx.py:L1-L935](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/ppt-expert/scripts/generate_pptx.py#L1-L935)）。
- 与 Anthropic 的 `pptx` skill 相比，当前流程偏向“生成”而缺少“template editing + QA loop + design system + pitfall control”的完整工作流。

## 主要 Gap（对标 Anthropic `pptx` skill）
- **Workflow coverage**：缺少 `template-based editing` 与 `from-scratch` 的分支流程与准入条件。
- **Design system**：缺少可执行的 `palette`、`typography`、`layout variation`、`spacing` 规则。
- **QA loop**：无 `content QA + visual QA + fix-and-verify` 机制。
- **Pitfall control**：缺少对 `PPTX` 生成常见问题的防护指引与规则化校验。
- **Deliverable quality bar**：没有明确“视觉完成度”的判定标准与拒绝条件。
- **Operational guidance**：缺少可复现的脚本链路与分工策略（例如并行编辑与审查）。

## 渐进式增强路线图（Design + Dev + Test）

### Phase 0：基线与可观测性（1-2 周）
- **Design**：定义 `Quality Bar` 与 `Reject Criteria`，明确“不可接受输出”的具体条件。
- **Dev**：在 skill 文档中加入 `Failure Handling` 细化规则与输出约束。
- **Test**：新增最小回归集（3-5 个代表性 deck）用于对比验证。

### Phase 1：Schema 与 Design System（2-3 周）
- **Design**：补充 `theme schema` 约束（palette dominance、font pairing、spacing scale）。
- **Dev**：在 `generate_pptx` 输入 JSON 上增加 `theme` 与 `layout` 建议字段解释。
- **Test**：覆盖 `theme` 覆写场景，验证字体/颜色/间距一致性。

### Phase 2：Layout 变体与内容映射（2-3 周）
- **Design**：定义 `content→layout mapping rules`（如 stats → cards, timeline → rows）。
- **Dev**：扩展 `slide type` 与 `layout variant`，加入“fallback to content slide”的规范。
- **Test**：构建 layout 多样性案例，确保非单一 bullet layout。

### Phase 3：QA Loop 标准化（2-3 周）
- **Design**：建立 `content QA` 与 `visual QA` 检查清单。
- **Dev**：在 skill 指令中强制 `fix-and-verify loop`，失败时必须再生成。
- **Test**：加入“视觉缺陷样例”，验证是否能识别并修复。

### Phase 4：Template Editing 能力（3-4 周）
- **Design**：引入 `template-based workflow`，定义模板选择、映射与编辑规范。
- **Dev**：补充 template 解析与抽取工具链（thumbnail/placeholder 标注）。
- **Test**：基于模板的替换与清理测试，验证 placeholder 清理完整度。

## 详细设计方案

### 1) Skill 文档结构升级（文档层）
- 新增 `Workflow` 分段：`Template Editing` 与 `From Scratch`。
- 新增 `Design System` 章节，固化 palette、typography、spacing、layout rhythm。
- 新增 `QA Checklist` 章节，包含 `content QA` 与 `visual QA`。

### 2) Schema 与生成策略（数据层）
- 扩展 `data.theme` 字段，明确 `primary/secondary/accent/background`。
- 增加 `layout_hint` 与 `visual_motif`，鼓励跨 slide 视觉一致性。
- 规范 `chart/table` 数据的最低输入要求与 fallback 逻辑。

### 3) Slide 变体与映射规则（逻辑层）
- 为 `content` 增加 `two_column` 自动拆分策略。
- 为 `stats` 与 `timeline` 设定条目上限与截断策略。
- 引入 `image_left/right` 的内容长度阈值规则。

### 4) QA Loop 标准（质量层）
- `Content QA`：缺字、顺序、空字段、placeholder 残留。
- `Visual QA`：overlap、overflow、alignment、contrast、spacing。
- `Fix-and-verify`：至少一轮修复与复验通过才允许输出。

## 开发实施计划（可执行项）

### A. 文档与规范
- 更新 `ppt-expert.md`，新增 `Workflow` 与 `QA Checklist`。
- 建立 `Skill QA` 检查清单文档模板，附带示例。

### B. 生成器能力增强
- 在 `generate_pptx.py` 内补充 `layout variants`。
- 加入 `theme` 合并与校验逻辑（如颜色格式与字号范围）。
- 扩展 `chart/table` 的容错逻辑与显式 fallback。

### C. 工具链与脚本
- 增加 `thumbnail` 与 `visual QA` 工具链的调用说明。
- 规范 `deck` 生成后的输出目录与文件命名策略。

## 测试计划（Test Plan）

### 1) 单元测试（Unit）
- `theme merge` 与 `schema validation`。
- `layout variant` 与 `fallback` 的输入边界测试。

### 2) 集成测试（Integration）
- 3 种 deck：Business update / Product roadmap / Research summary。
- 覆盖 `title + section + content + stats + timeline + chart + table`。

### 3) 视觉验证（Visual QA）
- 自动导出 slide images。
- 针对 overlap、overflow、contrast 的检查清单逐项验收。

### 4) 回归测试（Regression）
- 固定基线 deck 输出，对比内容完整性与 layout 多样性。

## 里程碑与交付物
- **M1**：Skill 文档升级 + QA checklist。
- **M2**：Theme schema 与 layout mapping 生效。
- **M3**：完整 QA loop 进入强制执行。
- **M4**：Template editing 路径可用并通过回归。

## 风险与缓解
- **风险**：QA loop 增加响应时长。  
  **缓解**：以 `deck size` 分级策略控制 QA depth。
- **风险**：layout 变体引入视觉不一致。  
  **缓解**：限定 `visual motif` 与 `spacing scale`。
- **风险**：模板替换导致 placeholder 残留。  
  **缓解**：强制执行 placeholder detection 与清理规则。
