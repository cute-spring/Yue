# Yue - 智能 AI 助手项目需求与进度文档

## 1. Project Overview (项目概述)

### 1.1 Project Background
I’ve built a personal AI chatbot that integrates:
- A DIY agent system with MCP (Model Context Protocol) for creating/selecting agents
- Multi-LLM support (ability to use different language models)
- Daily work facilitation features
- Advanced AI-powered personal notebook functionality

### 1.2 Current Status
The interface is functional but needs polish in usability, clarity, and user experience.

### 1.3 Technical Summary
Yue 是一个基于 Python (FastAPI) 和 SolidJS 构建的轻量级、高性能智能 AI 助手。它旨在提供一个类似 DeepSeek/ChatGPT 的极致交互体验，支持多种本地（Ollama）及远程（OpenAI, DeepSeek, 智谱）LLM 供应商，并具备插件化工具调用能力（MCP）。

---

## 2. 已实现功能 (Completed)

### 2.1 核心架构与存储
- [x] **后端服务**：基于 FastAPI 的异步架构。
- [x] **数据存储 (SQLite)**：从 JSON 迁移至 SQLite，支持并发安全与事务处理。
- [x] **对话记忆 (Context Management)**：支持多轮对话，自动携带最近 20 条消息上下文。
- [x] **数据自动迁移**：支持从旧版 `chats.json` 自动导入历史记录。

### 2.2 LLM 集成
- [x] **多供应商支持**：OpenAI, DeepSeek, 智谱 (GLM), Ollama。
- [x] **Ollama 自动探测**：自动发现本地运行的模型列表，无需手动配置。
- [x] **模型切换器**：内嵌于输入框的 UI 交互，支持供应商分组。
- [x] **鲁棒性处理**：模型不支持 Tool Call 时自动降级为纯聊天模式。

### 2.3 交互 UI (DeepSeek & Emerald Theme)
- [x] **三栏式布局**：侧边栏 (16px/250px) + 主聊天区 + 知识面板 (300px)。
- [x] **紧凑型图标轨**：全局侧边栏支持折叠为极简图标模式，解决 Phase 1 布局冲突。
- [x] **容器化输入框**：整合模型切换、功能按钮、文本输入的一体化设计。
- [x] **Markdown 渲染**：支持表格、引用、列表等精美排版。
- [x] **代码块增强**：Mac 风格窗口控制栏、语言标签、一键复制。
- [x] **数学公式渲染**：集成 KaTeX，支持行内 ($...$) 与块级 ($$ ... $$) 公式。
- [x] **思考过程展示**：DeepSeek R1 风格的折叠式推理链展示，UI 视觉升级。
- [x] **智能自动滚动**：生成时自动跟随，手动向上滚动时自动锁定位置。
- [x] **暗色模式支持**：完整的 Emerald Green 主题适配。

### 2.4 工具调用 (MCP)
- [x] **MCP 基础集成**：支持通过 MCP 协议调用外部工具（如 Filesystem）。
- [x] **角色 (Agent) 关联工具**：不同 Agent 可配置不同的工具集。

---

## 3. 开发中与计划中功能 (In Progress / Planned)

### 3.1 阶段 2：管理中心与工具体系 (Current Focus)
- [ ] **模型管理中心**：
    - [ ] **统一列表展示**：按类别（Premium, Advanced, Custom）分组展示已集成模型。
    - [ ] **自定义模型接入**：支持用户通过 UI 手动添加供应商、模型 ID 及 API Key。
- [ ] **Agent 管理中心**：
    - [ ] **可视化配置**：通过 UI 创建和编辑 Agent，支持设置名称、图标及详细 Prompt。
    - [ ] **智能 Prompt 生成**：集成 "Smart Generate" 功能。
    - [ ] **工具绑定管理**：支持为每个 Agent 独立勾选 MCP 工具或系统工具。
- [ ] **MCP 管理中心**：
    - [ ] **多模式添加**：支持从市场或手动配置 MCP Server。
    - [ ] **实时状态监控**：可视化展示 MCP Server 的连接状态。
    - [ ] **热开关管理**：一键开启/关闭特定的 MCP Server。
- [ ] **智能输入交互**：
    - [ ] **@提及系统**：快速切换 Agent。
    - [ ] **/斜杠指令**：快速执行操作（如 /search, /note）。

### 3.2 阶段 3：个人知识管理与多模态 (Next Steps)
- [ ] **多模态支持 (Upload Image/Doc)**：进度：[20%] (UI 占位已完成)。
- [ ] **智能知识面板**：相关笔记推荐、知识图谱可视化。
- [ ] **RAG 集成**：基于本地笔记库的检索增强生成。

### 3.3 系统稳定性与细节 (Planned)
- [ ] **Token 统计与费用预估**：实时统计每轮对话消耗。
- [ ] **多端自适应优化**：[90%] 已完成核心响应式设计。
- [ ] **AI 自动化增强**：会话标题 AI 总结、Deep Thinking 模式。

---

## 4. 当前技术栈
- **Frontend**: SolidJS, Tailwind CSS, Marked.js, Highlight.js, KaTeX.
- **Backend**: Python 3.10+, FastAPI, Pydantic AI, SQLite.
- **LLM Engine**: Ollama (Local), OpenAI/DeepSeek/Zhipu APIs.
- **Protocol**: Model Context Protocol (MCP).

---

## 5. 优化建议与未来发展 (Optimization Suggestions & Future Development)

### 5.1 用户体验优化建议 (User Experience Optimization)

**对话管理增强 (Conversation Management Enhancement)**：

- 实现对话历史搜索功能，支持关键词快速定位历史对话
- 添加对话标签系统，允许用户为重要对话添加自定义标签
- 引入对话文件夹功能，支持按项目/主题组织对话

**界面交互改进 (Interface Interaction Improvements)**：

- 考虑添加暗色主题切换，提升长时间使用的舒适度
- 实现可拖拽的对话气泡，支持重新排列对话顺序
- 添加快捷键支持（如Ctrl+Enter发送，Ctrl+N新建对话）

### 5.2 AI功能扩展建议 (AI Functionality Extensions)

**智能助手增强 (Intelligent Assistant Enhancement)**：

- 实现上下文感知的智能提示，根据当前对话内容推荐相关问题
- 添加AI助手个性化设置，允许用户自定义助手性格和回答风格

**知识管理升级 (Knowledge Management Upgrade)**：

- 构建个人知识图谱，自动提取和关联对话中的关键信息
- 实现智能摘要功能，为长对话生成简洁的摘要
- 添加知识导入功能，支持从各种文档格式构建个人知识库

### 5.3 技术架构优化建议 (Technical Architecture Optimization)

**性能优化 (Performance Optimization)**：

- 考虑实现消息的分页加载，提升大数据量下的响应速度
- 添加消息的本地缓存策略，减少重复请求
- 实现渐进式消息加载，优化网络传输效率

**扩展性提升 (Scalability Enhancement)**：

- 设计插件化架构，允许功能模块化扩展
- 实现统一的LLM调用管理和监控

### 5.4 个人数据安全与隐私 (Personal Data Security & Privacy)

**隐私保护 (Privacy Protection)**：

- 实现本地数据加密存储，保护个人敏感信息
- 添加数据导出/导入功能，支持用户完全掌控个人数据
- 优化对话内容的本地处理，最大限度减少敏感数据传输

### 5.5 UI/UX 设计优化建议 (UI/UX Design Optimization)

#### 5.5.1 布局结构优化
- [x] **三栏式智能布局**：侧边栏(16px/250px) + 主聊天区 + 知识面板(300px)
- [x] **响应式设计策略**：桌面端三栏，平板端可折叠，移动端单栏
- [x] **一体化输入框**：全宽度设计，支持多模态输入

#### 5.5.2 交互体验增强
- [ ] **智能输入体验**：@提及、快捷指令、上下文提示
- [x] **消息交互设计**：回复、引用、复制、保存为笔记操作 (已实现基础框架)
- [x] **思维过程展示**：可折叠/展开的推理链界面

#### 5.5.3 视觉设计系统
- [x] **设计系统建立**：统一的翡翠绿颜色系统、字体规范、间距系统
- [x] **暗色主题实现**：完整的深色模式支持
- [x] **动效设计原则**：微交互、平滑过渡、焦点管理

#### 5.5.4 功能区域优化
- [x] **侧边栏增强**：图标轨模式、智能对话历史、工具快捷方式
- [ ] **知识面板设计**：上下文相关笔记、智能推荐、快速操作
- [ ] **全局导航系统**：面包屑导航、快捷键支持、状态指示

#### 5.5.5 无障碍设计
- [ ] **键盘导航支持**：完整的键盘操作流程
- [ ] **屏幕阅读器优化**：ARIA标签和语义结构
- [ ] **个性化适配**：字体大小、布局偏好、交互方式调整

### 5.6 个人AI助手功能增强建议 (Personal AI Assistant Enhancement)

#### 5.6.1 智能知识管理功能
- [ ] **智能笔记分类系统**：AI自动分析内容生成标签，基于相似性自动归类
- [ ] **个人知识图谱构建**：实体关系提取，可视化知识网络，智能推荐关联
- [ ] **高级语义搜索能力**：基于含义的跨文档搜索，多维度筛选过滤

#### 5.6.2 AI写作助手增强
- [ ] **写作模板库**：技术文档、创意写作、学术论文等多场景模板
- [ ] **实时写作辅助**：语法纠错、表达优化、内容扩展
- [ ] **写作分析工具**：可读性分析、情感分析、关键词提取

#### 5.6.3 对话与笔记深度集成
- [ ] **对话转笔记功能**：一键保存重要对话，AI自动生成摘要
- [ ] **笔记增强对话**：上下文注入，基于个人知识库的个性化回答
- [ ] **智能上下文关联**：笔记与原始对话保持深度关联

### 5.7 具体实施优先级建议 (Implementation Priority)

**高优先级 (High Priority)**（建议立即实施）：

1. 完善多模态支持（图片上传和文档分析）
2. 实现对话搜索和标签功能
3. 模型与 Agent 管理中心可视化界面
4. 智能笔记分类和标签系统
5. 对话与笔记深度集成功能

**中优先级 (Medium Priority)**（后续迭代）：

1. 构建个人知识管理系统
2. 实现语音输入和输出功能
3. 开发插件化架构
4. 个人知识图谱构建
5. AI写作助手基础功能

**低优先级 (Low Priority)**（长期规划）：

1. 增强本地数据处理能力
2. 优化个人数据备份与迁移
3. 提升离线使用体验
4. 高级语义搜索和写作分析
5. 知识图谱可视化界面

---

## 6. 项目路线图 (Project Roadmap)

根据当前功能状态与 UI 设计规范，我们将开发划分为四个主要阶段：

### 阶段 1：视觉升级与布局重构 (Visual & Layout Foundation) - [COMPLETED]
**目标**：建立核心三栏式布局，统一视觉语言，提升基础对话体验。
- [x] **三栏式布局实现**：重构侧边栏（图标轨/250px）、主聊天区（自适应）、知识面板（300px）。
- [x] **视觉系统集成**：应用翡翠绿主题色，实现完整的暗色模式支持。
- [x] **一体化输入框升级**：整合模型切换、多模态按钮、智能高度调整。
- [x] **消息渲染优化**：完善推理链展示、代码块 Mac 风格装饰及 KaTeX 公式渲染。

### 阶段 2：管理中心与工具体系 (Management & Tooling) - [IN PROGRESS]
**目标**：实现模型、Agent 及 MCP 的可视化管理，增强工具调用能力。
- [ ] **模型管理中心**：实现 Premium/Advanced/Custom 分组管理及自定义模型接入。
- [ ] **Agent 管理编辑器**：支持可视化创建、Prompt 智能生成及工具绑定。
- [ ] **MCP 管理中心**：实现 Server 状态监控、开关管理及 Tools 详细列表展示。
- [ ] **智能输入交互**：实现 @提及 Agent 选择、/斜杠指令系统。

### 阶段 3：个人知识管理与多模态 (Knowledge & Multimodal)
**目标**：深化对话与个人知识库的集成，扩展感知维度。
- [ ] **智能知识面板**：实现上下文相关笔记推荐、知识图谱可视化。
- [ ] **多模态能力**：集成图片上传识图、多格式文档解析分析。
- [ ] **初级 RAG 集成**：实现基于本地笔记库的检索增强生成。
- [ ] **对话转笔记**：一键将对话精华保存至个人知识库，自动生成摘要。

### 阶段 4：智能化提升与极致体验 (Intelligence & Polishing)
**目标**：打磨细节，提供更具智能感的交互反馈。
- [ ] **AI 自动化增强**：会话标题 AI 总结、Deep Thinking 深度思考模式。
- [ ] **语音交互集成**：实现 Web Speech API 语音输入与 Whisper 适配。
- [ ] **性能与鲁棒性**：消息分页加载、本地缓存策略、Token 统计。
- [ ] **无障碍与快捷键**：完整的键盘导航支持（⌘K, ⌘N 等）与 ARIA 优化。

---

*更新日期：2026-02-01*
