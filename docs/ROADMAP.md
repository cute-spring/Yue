# Yue Project Development Roadmap

This document serves as a structured task list for AI development. Each phase is broken down into actionable items with specific technical requirements and UI/UX goals.

## Phase 1: Layout & Visual Foundation (视觉升级与布局重构) - [COMPLETED]
*Goal: Implement the core three-column layout and unify the design system.*

- [x] **1.1 Global Layout Reconstruction**
  - [x] Implement a three-column container: Sidebar (Compact icon rail / 250px), Chat Area (flex), Knowledge Panel (300px).
  - [x] Add responsive breakpoints: Full view (>1024px), Foldable sidebars (768px-1024px), Single column (<768px).
- [x] **1.2 Visual System Application**
  - [x] Apply Emerald Green (`#10B981`) as the primary brand color.
  - [x] Implement full Dark Mode support using CSS variables.
  - [x] Add smooth transitions (250ms ease-out) for panel toggling.
- [x] **1.3 Unified Input Center**
  - [x] Redesign the input box as a full-width container with floating action buttons.
  - [x] Integrate Model Switcher, Attachment button, and Voice input UI placeholders.
  - [x] Implement auto-expanding textarea (3 to 10 lines).
- [x] **1.4 Message UI Enhancements**
  - [x] Add Mac-style window controls to code blocks with language tags and copy buttons.
  - [x] Implement collapsible reasoning chains (Thought process) for R1-style models with enhanced visual hierarchy.
  - [x] Ensure KaTeX formulas and Markdown tables are rendered correctly.

## Phase 2: Management Centers & Tooling (管理中心与工具体系) - [COMPLETED]
*Goal: Provide visual interfaces for managing models, agents, and MCP servers.*

- ### Status Snapshot — Phase 2 (2026-02-07)
  - Completed
    - LLM config security: GET returns redacted values; POST ignores empty/masked keys to prevent accidental secret erasure.
    - Provider health check: `POST /api/models/test/{provider}` validates configuration by constructing the model.
    - MCP status API: `GET /api/mcp/status` reports `enabled/connected/last_error` per server; initialization respects `enabled`.
    - Stable tool IDs: `/api/mcp/tools` now returns `id = "server:name"`. Agent filtering accepts both legacy names and composite IDs.
    - Frontend: Settings → MCP status cards with Enable toggle; Save triggers reload and refresh. Settings → LLM adds “Test Connection”.
    - Agent editor: adds directory scope input for docs_search/docs_read via root_dir and persists `doc_roots`.
    - Agent editor: adds “Smart Generate” (UI + `POST /api/agents/generate`) to generate name/prompt/tool suggestions and auto-fill the form.
    - Agents list: displays configured doc scope tags for quick visibility.
    - Chat runtime: system prompt appends configured doc scopes when present.
    - Smart Generate Enhancements: Tool recommendations with reasons and risk classification (read/write/network) are fully implemented in the backend and visible in UI.
    - Local Docs Retrieval: Full support for text-like and PDF files with unified tools, directory access control (`allow_roots`), and citation display in Chat UI.
  - Verified
    - Backend hot-reload clean; endpoints tested successfully.
    - Frontend dev server running; production build succeeded via `npm run build`.
    - E2E tests for Smart Generate and Chat commands passed.
  - Known Notes
    - A transient cancellation error was observed during one MCP reload; subsequent reloads succeeded and status remained correct.
  - Next Steps
    - [ ] Add schema validation on MCP config saves for friendlier errors.
    - [x] Migrate existing agents’ `enabled_tools` to composite IDs on edit/save for full consistency.
    - [ ] Extend backend tests to cover provider tests, MCP status, and config updates.

- ### Local Docs Retrieval Roadmap (本地文档检索路线图：P0–P3)
  - [x] **Phase 1 (Done): Text-like docs support + unified tools**
    - [x] Support extension allowlist for local reads/searches: `.md/.txt/.log/.json/.yaml/.yml/.csv`
    - [x] Provide unified builtin tools:
      - [x] `builtin:docs_search(query, mode, root_dir?, limit?, max_files?, timeout_s?)`
      - [x] `builtin:docs_read(path, mode, root_dir?, start_line?, max_lines?)`
    - [x] Keep legacy `builtin:docs_*_markdown*` as wrappers for compatibility
  - [x] **P0: Doc access config management (可视化配置白名单/黑名单)**
    - [x] Add `POST /api/config/doc_access` to update `allow_roots/deny_roots`
    - [x] Add Settings UI for managing `doc_access` and persisting changes
  - [x] **P1: Retrieval quality & guardrails (检索质量与安全护栏)**
    - [x] Improve snippet locator (line window + line ranges) for `docs_search`
    - [x] Add search limits (e.g. `max_total_bytes_scanned`) to avoid scanning huge folders
    - [x] Add include/exclude patterns for practical directory filtering (optional)
  - [x] **P2: PDF support (PDF 解析与检索)**
    - [x] Add PDF read/search tools with strict caps: max pages/bytes/timeout
    - [x] Normalize citations to include page ranges when available
  - [x] **P3: Citation enforcement & UX (强制引用输出与体验完善)**
    - [x] Enforce citations for doc-grounded agents at chat API output gate
    - [x] Display citations in Chat UI as a structured list (path + locator)

- [x] **2.1 Model Management Center**
  - [x] Create a management page with grouped lists: Premium, Advanced, and Custom models.
  - [x] Build UI for adding custom models (Provider, Model ID, API Key fields).
  - [x] Add provider connection test action ("Test Connection").
- [x] **2.2 Agent Configuration Editor**
  - [x] Implement the Agent creation/edit modal based on the reference design.
  - [x] Add "Smart Generate" button to assist in writing Agent prompts via LLM.
  - [x] Implement tool-binding checklists for both MCP tools and Built-in tools.
  - [x] **2.2.1 Smart Generate Enhancements (Smart Agent Factory)**
    - [x] Add draft preview with partial apply (Name / Prompt / Tools).
    - [x] Add tool recommendation explanations and risk badges (read-only / write / network).
    - [ ] Add pre-publish checks: prompt lint + 1-shot self-test preview before creating/updating.
    - [ ] Add safety policy: tool limits and second-confirm for risky tools.
    - [ ] Add audit trail and rollback for agent config changes.
    - [ ] Add template library with variableized generation presets (Docs QA / Code Reviewer / Researcher / Translator).
    - [x] Add doc_roots picker and validation hints when docs_search/docs_read are enabled.
    - [x] Strengthen structured generation schema and fallback behavior (e.g., prompt-only on JSON failure).
    - [x] Add E2E test for Smart Generate: generate → auto-fill → save → edit consistency.
    - [ ] Add metrics: generation success rate, post-publish edit rate, and failure reasons.
- [x] **2.3 MCP Management Dashboard**
  - [x] Display connected MCP servers with status indicators (Online/Offline).
  - [x] Add a toggle switch for hot-enabling/disabling specific MCP servers.
  - [x] Implement an expandable view to list available tools for each MCP server.
- [x] **2.4 Smart Interaction Logic**
  - [x] Implement `@` mention system to quickly switch between Agents/Tools in the input box.
  - [x] Add `/` slash command system (e.g., `/search`, `/note`, `/help`).

- [ ] **2.5 MCP Ecosystem & Connectors Expansion (MCP 工具库与连接器扩展)**
  - **Core Extension Directions (核心扩展方向)**
    - [ ] **Built-in Connectors**:
      - [ ] Web Search Connector (Tavily/DuckDuckGo integration).
      - [ ] Advanced Code Analysis (AST-aware navigation/search).
      - [ ] Structured Data Handler (CSV/Excel/JSON analysis).
      - [ ] Secure File Writer (with HITL audit for controlled editing).
    - [ ] **External Ecosystem Integration**:
      - [ ] Project Management: **JIRA** & **Confluence** integration.
      - [ ] Version Control: **GitHub** management.
      - [ ] Communication: **Microsoft Teams** notification & relay.
      - [ ] **Generic OpenAPI Adapter**: Zero-code integration for internal systems via OpenAPI/Swagger specs (通用 OpenAPI 适配器).
   - **Technical Evolution (技术演进)**
     - [ ] **Phase 1: Connectivity & Reliability**:
       - [ ] Implement SSE (Server-Sent Events) support for remote MCP servers.
       - [ ] Connection pool management with auto-reconnect and health checks.
       - [ ] **Credential Vault**: Visual API Key/Token management with expiration alerts (凭证保险箱与过期提醒).
     - [ ] **Phase 2: Semantic Intelligence**:
       - [ ] Semantic Tool Routing: Dynamically load tools based on user intent.
       - [ ] Zero-code plugin configuration via UI/URL.
     - [ ] **Phase 3: Governance & Security**:
       - [ ] Fine-grained RBAC for tool access at the Agent level.
       - [ ] Comprehensive audit trail and latency metrics for all tool calls.
   - **UX/DX Enhancements**:
     - [ ] Visual Tool Preview: Test-run tools in the Settings/Management UI.
     - [ ] MCP Server Templates: Rapid development scaffolds for custom connectors.
     - [ ] **Impact Preview (Dry Run)**: Visual "Diff View" for write operations before final approval (写操作副作用预览与二次确认).
  - [x] **Safety & Compliance (安全与合规)**:
    - [x] Data Minimization: Built-in tools return only necessary fields and summarized snippets; PDF/text reads enforce max snippet length with hash markers (数据最小化策略).
    - [x] Tool Risk Classification: Show risk level per tool (read/write/network/external) with second-confirm and audit logs (工具风险分级).
  - [ ] **Reliability & Performance (可靠性与性能)**:
    - [ ] Tool Call Budget: Set per-chat call/time limits with explicit degradation message when budget is exhausted (工具调用预算).
    - [ ] Retrieval Regression Suite: Golden queries for docs_search/docs_read/PDF with P95/P99 latency and hit-rate gates (检索质量回归集).
  - [ ] **Engineering & Maintainability (工程化与可维护性)**:
    - [ ] Tool Schema Versioning: Versioned tool input/output with backward-compatible adapters to prevent MCP updates breaking clients (工具协议锁定与版本化).
    - [ ] Developer Sandbox Mode: Local sandbox in Settings; write operations become Dry Run with planned API request output (开发者沙箱).
    - [ ] Expanded Test Matrix: Add backend coverage for unauthorized tool calls, missing citations, large scan timeout/limit (自动化测试矩阵扩展).
  - [x] **Intelligent Orchestration & UX (智能编排与体验)**:
    - [ ] Semantic Tool Retrieval: Vector index over tool name/description/schema, attach Top-K tools by intent (语义化工具检索).
    - [x] Minimal Citation Cards: Show concise source cards (path/snippet/locator) with copy/jump and auto-collapse long excerpts (引用卡片最小化设计).
  - [ ] **Security Config & Observability (安全配置与凭证管理)**:
    - [ ] Credential Rotation & Health Checks: Token expiry alerts and one-click checks for JIRA/GitHub/Teams; MCP init preflight (凭证轮换与健康检查).
    - [ ] MCP Metrics Panel: Real-time success/latency/deny/timeout metrics in Settings → MCP (可观测性面板).

## Phase 3: Knowledge Integration & Multimodal (个人知识管理与多模态) - [IN PROGRESS]
*Goal: Connect chat context with personal notes and expand sensing capabilities.*

- ### Status Snapshot — Phase 3 (2026-02-07)
  - Completed
    - Multimodal: Image upload UI implemented in Chat.
    - Doc Parsing: Support for PDF, Markdown, and Txt parsing in retrieval service.
    - Chat to Note: `/note` command saves the last message as a note with an auto-generated title.
    - Knowledge Panel: "Notes" tab in Intelligence Hub displays saved notes.
  - Next Steps
    - Implement Knowledge Graph visualization (basic entity relation view).
    - Migrate from keyword-based search to vector-based RAG using SQLite/Simple vector store.

- [x] **3.1 Intelligent Knowledge Panel**
  - [x] Implement logic to fetch and display "Contextually Relevant Notes" based on current chat topics.
  - [ ] Add a toggleable Knowledge Graph visualization (basic entity relation view).
- [x] **3.2 Multimodal Processing**
  - [x] Enable image upload and processing for Vision-capable models.
  - [x] Implement document parsing (PDF, Markdown, Txt) and inject content into LLM context.
- [x] **3.3 RAG (Retrieval-Augmented Generation) Integration**
  - [ ] Build a local vector search pipeline using SQLite/Simple vector store.
  - [x] Implement "Search-Augmented Chat" where the AI queries personal notes before answering (current: keyword search).
- [x] **3.4 "Chat to Note" Workflow**
  - [x] Add an action button to messages to "Save as Note" (implemented via `/note`).
  - [x] Auto-generate a concise summary and title for saved notes using LLM.

## Phase 4: Intelligence & Polish (智能化提升与极致体验)
*Goal: Refine micro-interactions and add advanced AI features.*

- [ ] **4.1 Advanced AI Features**
  - [x] Implement automatic session title generation after the first few messages.
  - [ ] Add "Deep Thinking" mode toggle for non-reasoning models via prompt engineering.
- [ ] **4.2 Voice & Accessibility**
  - Integrate Web Speech API for voice-to-text input.
  - Complete ARIA label coverage and keyboard navigation support (Cmd+K for search, Cmd+N for new chat).
- [ ] **4.3 Performance Optimization**
  - Implement message pagination/lazy loading for long conversation histories.
  - Add local caching for messages and agent configurations to reduce latency.
  - Integrate Token usage statistics and estimated cost display.

## Phase 5: Technical Debt & Stability (技术债治理与稳定性) - [IN PROGRESS]
*Goal: Address architectural limitations and improve system robustness based on [Chat_System_Analysis_Report.md](./Chat_System_Analysis_Report.md).*

- [x] **5.1 Architecture & Database**
  - [x] Enable SQLite WAL mode (`PRAGMA journal_mode=WAL`) for better concurrency.
  - [x] Add index `idx_messages_session_id` to `messages` table for query performance.
  - [ ] Implement database connection pooling to handle concurrent write requests safely.
  - [ ] Evaluate migration path from SQLite to PostgreSQL for high-concurrency scenarios.
- [x] **5.2 Feature Completeness**
  - [x] **Backend Multimodal Support**: Added `images` column to DB schema and updated `chat_service.py` to persist uploaded images as local files.
  - [x] **Vision API Integration**: Connected backend to Pydantic AI's `ImageUrl` support.
  - [ ] **True RAG Implementation**: Replace hardcoded "doc search" prompt with Vector DB + Embedding pipeline.
- [x] **5.3 Error Handling & Observability**
  - [x] **Frontend**: Replaced empty `catch` blocks with global Toast notifications.
  - [ ] **Backend**: Replace `print` statements with standard `logging` module.
  - [ ] **Resilience**: Replace string-matching error handling with capability-based checks.
- [ ] **5.4 Context Management**
  - [ ] **Smart Summary**: Implement "Rolling Summary" to compress old history instead of hard truncation.
  - [ ] **Precise Token Counting**: Integrate `tiktoken` for accurate token estimation (replacing `len/3` heuristic).

---
*Last Updated: 2026-02-07*
