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
- [ ] **模型管理中心**：
    - [ ] **统一列表展示**：按类别（Premium, Advanced, Custom）分组展示已集成模型。
    - [ ] **自定义模型接入**：支持用户通过 UI 手动添加供应商、模型 ID 及 API Key。
    - [ ] **可视化管理**：提供模型的类型、供应商信息及快捷管理操作。

### 2.3 交互 UI (DeepSeek 风格)
- [x] **容器化输入框**：整合模型切换、功能按钮、文本输入的一体化设计。
- [x] **Markdown 渲染**：支持表格、引用、列表等精美排版。
- [x] **代码块增强**：Mac 风格窗口控制栏、语言标签、一键复制。
- [x] **数学公式渲染**：集成 KaTeX，支持行内 ($...$) 与块级 ($$ ... $$) 公式。
- [x] **思考过程展示**：DeepSeek R1 风格的折叠式推理链展示。
- [x] **智能自动滚动**：生成时自动跟随，手动向上滚动时自动锁定位置。

### 2.4 工具调用 (MCP)
- [x] **MCP 基础集成**：支持通过 MCP 协议调用外部工具（如 Filesystem）。
- [x] **角色 (Agent) 关联工具**：不同 Agent 可配置不同的工具集。
- [ ] **Agent 管理中心**：
    - [ ] **可视化配置**：通过 UI 创建和编辑 Agent，支持设置名称、图标及详细 Prompt。
    - [ ] **智能 Prompt 生成**：集成 "Smart Generate" 功能，辅助用户编写高质量 Agent 指令。
    - [ ] **权限与协作控制**：支持设置 Agent 是否可被其他 Agent 调用（Multi-Agent Collaboration）。
    - [ ] **工具绑定管理**：支持为每个 Agent 独立勾选已连接的 MCP 工具或内置系统工具（Read, Edit, Terminal）。
- [ ] **MCP 管理中心**：
    - [ ] **多模式添加**：支持从市场（Marketplace）添加或手动（Manually）配置 MCP Server。
    - [ ] **实时状态监控**：可视化展示 MCP Server 的连接状态（在线/离线）。
    - [ ] **热开关管理**：支持一键开启/关闭特定的 MCP Server。
    - [ ] **详细信息扩展**：可折叠查看 MCP Server 提供的具体 Tools 列表及配置参数。

---

## 3. 开发中与计划中功能 (In Progress / Planned)

### 3.1 增强功能 (In Progress)
- [ ] **多模态支持 (Upload Image)**：
    - 进度：[20%] (UI 占位已完成)
    - 目标：支持上传图片并调用具备 Vision 能力的模型进行识图。
- [ ] **文档分析 (Upload Document)**：
    - 进度：[10%] (UI 占位已完成)
    - 目标：支持 PDF/Markdown/Txt 文档解析并作为 Context 喂给模型。
- [ ] **语音输入 (Voice Input)**：
    - 进度：[10%] (UI 占位已完成)
    - 目标：集成浏览器 Web Speech API 或 Whisper 实现语音转文字。

### 3.2 体验优化 (Planned)
- [ ] **深度思考模式 (Deep Thinking)**：
    - 进度：[30%] (UI 开关已完成)
    - 目标：对于非推理模型，通过 Prompt 工程强制开启思维链输出。
- [ ] **会话标题 AI 生成**：
    - 进度：[50%] (目前使用首句截断)
    - 目标：对话完成后，调用模型自动总结更精准的会话标题。
- [ ] **搜索增强 (RAG)**：
    - 进度：[0%]
    - 目标：集成本地知识库，实现基于文档的问答。

### 3.3 系统稳定性 (Planned)
- [ ] **Token 统计与费用预估**：
    - 进度：[0%]
    - 目标：实时统计每轮对话消耗的 Token。
- [ ] **多端自适应优化**：
    - 进度：[70%]
    - 目标：进一步优化移动端窄屏下的聊天体验。

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
- [ ] **三栏式智能布局**：侧边栏(250px) + 主聊天区 + 知识面板(300px)
- [ ] **响应式设计策略**：桌面端三栏，平板端可折叠，移动端单栏
- [ ] **一体化输入框**：全宽度设计，支持多模态输入

#### 5.5.2 交互体验增强
- [ ] **智能输入体验**：@提及、快捷指令、上下文提示
- [ ] **消息交互设计**：回复、引用、复制、保存为笔记操作
- [ ] **思维过程展示**：可折叠/展开的推理链界面

#### 5.5.3 视觉设计系统
- [ ] **设计系统建立**：统一的颜色系统、字体规范、间距系统
- [ ] **暗色主题实现**：完整的深色模式支持
- [ ] **动效设计原则**：微交互、平滑过渡、焦点管理

#### 5.5.4 功能区域优化
- [ ] **侧边栏增强**：智能对话历史、工作空间管理、工具快捷方式
- [ ] **知识面板设计**：上下文相关笔记、智能推荐、快速操作
- [ ] **全局导航系统**：面包屑导航、快捷键支持、状态指示

#### 5.5.5 无障碍设计
- [ ] **键盘导航支持**：完整的键盘操作流程
- [ ] **屏幕阅读器优化**：ARIA标签和语义结构
- [ ] **个性化适配**：字体大小、布局偏好、交互方式调整

#### 5.5.4 功能区域优化
- [ ] **侧边栏增强**：智能对话历史、工作空间管理、工具快捷方式
- [ ] **知识面板设计**：上下文相关笔记、智能推荐、快速操作
- [ ] **全局导航系统**：面包屑导航、快捷键支持、状态指示

#### 5.5.5 无障碍设计
- [ ] **键盘导航支持**：完整的键盘操作流程
- [ ] **屏幕阅读器优化**：ARIA标签和语义结构
- [ ] **个性化适配**：字体大小、布局偏好、交互方式调整



### 5.5 个人AI助手功能增强建议 (Personal AI Assistant Enhancement)

#### 5.5.1 智能知识管理功能
- [ ] **智能笔记分类系统**：AI自动分析内容生成标签，基于相似性自动归类
- [ ] **个人知识图谱构建**：实体关系提取，可视化知识网络，智能推荐关联
- [ ] **高级语义搜索能力**：基于含义的跨文档搜索，多维度筛选过滤

#### 5.5.2 AI写作助手增强
- [ ] **写作模板库**：技术文档、创意写作、学术论文等多场景模板
- [ ] **实时写作辅助**：语法纠错、表达优化、内容扩展
- [ ] **写作分析工具**：可读性分析、情感分析、关键词提取

#### 5.5.3 对话与笔记深度集成
- [ ] **对话转笔记功能**：一键保存重要对话，AI自动生成摘要
- [ ] **笔记增强对话**：上下文注入，基于个人知识库的个性化回答
- [ ] **智能上下文关联**：笔记与原始对话保持深度关联

### 5.6 具体实施优先级建议 (Implementation Priority)

**高优先级 (High Priority)**（建议立即实施）：

1. 完善多模态支持（图片上传和文档分析）
2. 实现对话搜索和标签功能
3. 添加暗色主题和界面个性化选项
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
*更新日期：2026-01-31*
