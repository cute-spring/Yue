# 2026-06-01 ChatSidebar UI/UX 重构落地方案

## 目标
将 `ChatSidebar` 从“配置区堆叠的侧栏”升级为“主任务优先、上下文清晰、资源按需展开”的产品级工作侧栏。

核心结果：
- 首屏优先展示聊天搜索与历史列表
- Workspace 上下文更清晰，但不抢占过多高度
- Sources / Artifacts 从常驻展开改为摘要化、折叠化
- 提升窄栏可读性、状态扫描效率和操作一致性

## 当前问题
基于 [`frontend/src/components/ChatSidebar.tsx`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatSidebar.tsx:333) 当前实现，存在以下问题：

1. 顶部管理区高度过大
- `Workspace`、`Sources`、`Artifacts`、搜索框全部堆在顶部固定区。
- 侧栏固定宽度为 `260px`，但顶部区内容密度高，压缩了聊天历史首屏可见条目数。

2. 主任务与次任务层级倒挂
- 用户高频任务是搜索聊天、切换聊天、开始新聊天。
- 当前视觉上更突出的却是工作区创建、资料模式切换、Artifacts 详情。

3. 低频操作暴露过度
- `Create workspace` 输入框和 `Add` 按钮始终显示。
- `Sources` 默认同时展示模式切换、grounding 模式、evidence 摘要和完整列表。

4. 视觉负担偏重
- 顶部三个区块都使用完整卡片样式：`rounded-xl + border + shadow-sm`。
- 在窄栏中容易显得拥挤、碎片化、管理感过强。

5. 信息被截断但缺少补偿
- source 名称、artifact 标题、artifact 路径均大量依赖 `truncate`。
- 缺少 tooltip 或其他“查看完整内容”的补偿设计。

## 设计原则
本次重构遵循以下 UI/UX 原则：

1. 主任务优先
- 搜索聊天、切换聊天、新建聊天应优先获得首屏空间和视觉权重。

2. 渐进披露
- 低频管理内容默认摘要化，按需展开。

3. 轻分区优于重卡片
- 在高密度侧栏中优先使用 section、分隔线、留白建立层级，而不是连续卡片。

4. 上下文先于控制项
- 先让用户看懂“当前在哪个 workspace、当前资源状态如何”，再暴露详细控制。

5. 紧凑但可读
- 控件要收紧，但不能牺牲可读性、键盘可达性和状态辨识度。

## 目标信息架构
重构后侧栏结构建议如下：

1. `Workspace Context Bar`
2. `Search + New Chat`
3. `Resources Summary` 折叠区
4. `Chat History`
5. `History Footer`

说明：
- `Workspace` 负责“当前上下文”
- `Resources` 负责“当前工作区资料状态与管理”
- `Chat History` 保持为主工作面

## 目标交互结构

### 1. Workspace Context Bar
将当前 `Workspace` 卡片改成紧凑型上下文条。

#### 结构
- 左侧：
  - label: `Workspace`
  - 当前 workspace 名称
- 右侧：
  - workspace 切换入口
  - `+ New` 按钮

#### 行为
- 默认仅展示当前 workspace 名称，不额外重复一行说明文字。
- 点击 `+ New` 后展开内联创建输入区。
- 创建完成后自动收起输入区并恢复为紧凑条。
- loading 时仅在右侧显示小型状态反馈，不独立占据显著区域。

#### 落地建议
- 替换当前 [`334-378`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatSidebar.tsx:334) 整块卡片结构。
- `Create workspace` 输入区改为条件渲染，不常驻显示。

### 2. Search + New Chat
将搜索和新建聊天提升为顶部高优先级操作区。

#### 结构
- 左侧：搜索框
- 右侧：`New Chat` 主按钮

#### 行为
- 搜索框位置保持稳定，不随资源展开而跳动。
- `New Chat` 保持明确的主色按钮风格。
- 该区放在 Workspace Context Bar 下方、Resources 之上。

#### 目标
- 打开侧栏后，用户无需先滚过配置区才能进入聊天。

### 3. Resources Summary
将 `Sources` 与 `Artifacts` 重构为一个统一的资源折叠区。

#### 顶层摘要
顶层仅显示：
- `Resources`
- 当前数量摘要，例如：`5 sources · 2 artifacts`
- 关键状态摘要，例如：`3 cite-ready`
- 展开/收起图标

#### 展开后结构
展开后分两段：

1. `Sources`
- 数量
- source mode 摘要
- grounding mode 摘要
- evidence scope 摘要
- 展开明细按钮

2. `Artifacts`
- 数量
- 最近 artifact 标题或简短摘要
- 展开明细按钮

#### 二级展开
建议 `Resources` 下的 `Sources`、`Artifacts` 都支持各自折叠。

默认规则：
- 无 workspace：`Resources` 收起，仅显示提示文案
- 有 workspace 且 sources 未配置完成：首次自动展开 `Sources`
- 有 artifacts 但数量较多：默认折叠 `Artifacts`

#### 落地建议
- 替换当前 [`380-640`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatSidebar.tsx:380) 的双大卡片结构。
- 不再默认直接展示全部 source 列表和 artifact 详情。

### 4. Chat History
聊天历史保留当前分组折叠逻辑，但进一步强化主列表属性。

#### 保留项
- 日期分组
- sticky group header
- 当前会话高亮
- hover 操作按钮

#### 优化项
- 首屏可见会话数提升
- 空状态与过滤状态继续保留
- 搜索和过滤属于历史列表的配套功能，不应被资源管理区挤压

## 视觉规范

### 整体风格
- 从“三张白卡片”改为“轻分区 + 少量强调”
- 减少阴影，保留边界和留白
- 让聊天列表成为视觉主体，资源区成为次级上下文

### 分区样式
- `Workspace Context Bar`：轻背景、细边框、低高度
- `Search + New Chat`：与历史区保持连续感
- `Resources Summary`：使用 section 样式，不使用厚重卡片
- `Chat History`：保持当前简洁列表风格

### 间距建议
- 顶部上下文条：`px-4 py-3`
- 搜索区：`px-4 py-2`
- 折叠摘要行：`px-4 py-2`
- 展开内容区：`px-4 pb-3`
- 列表项内部 padding 再收紧一个档位，优先保留文本空间

### 字体层级
- section label：`text-[10px] uppercase tracking-wide`
- 当前 workspace 名称：`text-sm font-semibold`
- 摘要说明：`text-[11px] text-slate-500`
- 次级元信息：`text-[10px] text-slate-400`

### 色彩建议
- 主强调色仅保留给：
  - 当前会话
  - 新建聊天按钮
  - 关键状态
- `Resources` 相关状态以中性色和少量功能色表达，不与主任务抢视觉权重

## 信息摘要规则

### Workspace
- 默认显示当前 workspace 名称
- 未选择时显示 `All Workspaces`

### Sources
- 摘要优先展示：
  - 总数
  - cite-ready 数
  - 当前 source mode
  - grounding mode

示例：
- `5 sources`
- `3 cite-ready`
- `Mode: Selected`
- `Grounding: Prefer cites`

### Artifacts
- 摘要优先展示：
  - 总数
  - 最新一条 artifact 标题
  - 是否关联 chat

示例：
- `2 artifacts`
- `Latest: Q2 synthesis memo`

## 细节交互规范

### 创建 Workspace
- 默认隐藏输入区
- 点击 `+ New` 后展开
- `Esc` 收起
- 创建成功后清空并收起

### 截断信息补偿
为以下内容增加 `title` 或 tooltip：
- workspace 名称
- source 名称
- artifact 标题
- artifact 路径

### 折叠一致性
- 所有可折叠 section 使用同一套 chevron 方向与动画
- open / closed 的 header 背景、计数、hover 状态保持一致

### 按钮样式
- `Retry`、`Check` 等管理型动作降低视觉权重
- `New Chat` 保持最高操作优先级

## 可访问性要求

1. 所有折叠区按钮使用 `aria-expanded`
2. 创建 workspace 的展开按钮带可读 label
3. tooltip 信息需至少可通过原生 `title` 获得
4. 键盘可以完成：
- 展开/收起 resources
- 展开/收起 sources / artifacts
- 创建 workspace
- 搜索聊天
- 切换聊天

## 实施分期

### Phase 1: 信息架构重构
目标：先把层级改对。

任务：
- 将 `Workspace` 重构为 context bar
- 将搜索区上移
- 将 `Sources + Artifacts` 合并为 `Resources`
- 保留现有历史列表逻辑

验收：
- 打开侧栏时，历史列表明显更早进入视野
- 顶部不再出现三张连续大卡片

### Phase 2: 资源摘要化与折叠逻辑
目标：降低管理区默认复杂度。

任务：
- `Resources` 顶层摘要化
- `Sources`、`Artifacts` 二级折叠
- 默认展开规则按状态控制

验收：
- 普通聊天流程中，用户不需要先看完整 sources/artifacts 才能操作
- 有 workspace 时仍能快速感知资料状态

### Phase 3: 可读性与微交互打磨
目标：修掉窄栏细节体验问题。

任务：
- 为截断内容补 tooltip
- 统一 chevron 和折叠动效
- 收紧 padding 和 chip 数量
- 优化 hover/focus 状态

验收：
- 长标题和路径不再只能看见截断内容
- 交互反馈更统一

## 组件拆分建议
如果允许小幅重构，建议拆分为：

- `ChatSidebarWorkspaceBar`
- `ChatSidebarSearchBar`
- `ChatSidebarResources`
- `ChatSidebarHistoryList`

收益：
- 顶部管理结构更容易独立迭代
- 历史列表逻辑与资源管理逻辑解耦
- 后续更方便做响应式或 A/B 调整

如果当前不希望拆分组件，也至少应先做 JSX 结构分段和局部状态整理。

## 状态建议
新增本地 UI state：

```ts
const [showCreateWorkspace, setShowCreateWorkspace] = createSignal(false);
const [isResourcesExpanded, setIsResourcesExpanded] = createSignal(false);
const [isSourcesExpanded, setIsSourcesExpanded] = createSignal(false);
const [isArtifactsExpanded, setIsArtifactsExpanded] = createSignal(false);
```

建议增加初始化策略：
- 首次进入有 workspace 且 sources 未就绪时，自动展开 `Resources` 和 `Sources`
- 其他场景默认收起 `Resources`

## 风险与取舍

1. 风险：资料管理入口被藏太深
- 应对：顶层摘要必须足够清楚，并保留明显计数和状态

2. 风险：展开层级过多
- 应对：只允许两层折叠，不做更深层级

3. 风险：实现时一次性改太多
- 应对：按三期实施，先改结构，再改摘要，最后打磨

## 验收清单

1. 侧栏首屏可见聊天项数量明显增加
2. 当前 workspace 一眼可见
3. 创建 workspace 不再常驻占位
4. Sources / Artifacts 默认不再全部展开
5. 用户可以在不展开资源区的情况下完成常用聊天操作
6. 被截断的长文本可通过 hover 或 title 查看完整内容
7. 键盘可完成核心导航和折叠操作

## 推荐实施顺序

1. 调整顶层 DOM 结构
2. 引入 `Resources` 折叠 state
3. 收起 `Create workspace`
4. 加摘要文案与数量状态
5. 补 tooltip / `title`
6. 最后微调 spacing、边框、hover 和动画

## 结论
这次不是单纯做“样式优化”，而是一次侧栏任务模型重排。

最终落地方向应明确为：
- 让聊天历史重新成为主工作面
- 让 workspace 成为轻量上下文
- 让 resources 成为按需展开的辅助区

如果按本方案执行，`ChatSidebar` 会从“工程上可用的配置面板”升级成“更符合高频聊天工作流的产品级侧栏”。
