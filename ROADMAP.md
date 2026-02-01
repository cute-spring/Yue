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

## Phase 2: Management Centers & Tooling (管理中心与工具体系) - [IN PROGRESS]
*Goal: Provide visual interfaces for managing models, agents, and MCP servers.*

- ### Status Snapshot — Phase 2 (2026-02-01)
  - Completed
    - LLM config security: GET returns redacted values; POST ignores empty/masked keys to prevent accidental secret erasure.
    - Provider health check: `POST /api/models/test/{provider}` validates configuration by constructing the model.
    - MCP status API: `GET /api/mcp/status` reports `enabled/connected/last_error` per server; initialization respects `enabled`.
    - Stable tool IDs: `/api/mcp/tools` now returns `id = "server:name"`. Agent filtering accepts both legacy names and composite IDs.
    - Frontend: Settings → MCP status cards with Enable toggle; Save triggers reload and refresh. Settings → LLM adds “Test Connection”.
  - Verified
    - Backend hot-reload clean; endpoints tested successfully.
    - Frontend dev server running; production build succeeded via `npm run build`.
  - Known Notes
    - A transient cancellation error was observed during one MCP reload; subsequent reloads succeeded and status remained correct.
  - Next Steps
    - Add schema validation on MCP config saves for friendlier errors.
    - Migrate existing agents’ `enabled_tools` to composite IDs on edit/save for full consistency.
    - Extend backend tests to cover provider tests, MCP status, and config updates.

- [ ] **2.1 Model Management Center**
  - [ ] Create a management page with grouped lists: Premium, Advanced, and Custom models.
  - [ ] Build a modal for adding custom models (Provider, Model ID, API Key fields).
- [ ] **2.2 Agent Configuration Editor**
  - [ ] Implement the Agent creation/edit modal based on the reference design.
  - [ ] Add "Smart Generate" button to assist in writing Agent prompts via LLM.
  - [ ] Implement tool-binding checklists for both MCP tools and Built-in tools.
- [ ] **2.3 MCP Management Dashboard**
  - [ ] Display connected MCP servers with status indicators (Online/Offline).
  - [ ] Add a toggle switch for hot-enabling/disabling specific MCP servers.
  - [ ] Implement an expandable view to list available tools for each MCP server.
- [ ] **2.4 Smart Interaction Logic**
  - [ ] Implement `@` mention system to quickly switch between Agents/Tools in the input box.
  - [ ] Add `/` slash command system (e.g., `/search`, `/note`, `/help`).

## Phase 3: Knowledge Integration & Multimodal (个人知识管理与多模态)
*Goal: Connect chat context with personal notes and expand sensing capabilities.*

- [ ] **3.1 Intelligent Knowledge Panel**
  - Implement logic to fetch and display "Contextually Relevant Notes" based on current chat topics.
  - Add a toggleable Knowledge Graph visualization (basic entity relation view).
- [ ] **3.2 Multimodal Processing**
  - Enable image upload and processing for Vision-capable models.
  - Implement document parsing (PDF, Markdown, Txt) and inject content into LLM context.
- [ ] **3.3 RAG (Retrieval-Augmented Generation) Integration**
  - Build a local vector search pipeline using SQLite/Simple vector store.
  - Implement "Search-Augmented Chat" where the AI queries personal notes before answering.
- [ ] **3.4 "Chat to Note" Workflow**
  - Add an action button to messages to "Save as Note".
  - Auto-generate a concise summary and title for saved notes using LLM.

## Phase 4: Intelligence & Polish (智能化提升与极致体验)
*Goal: Refine micro-interactions and add advanced AI features.*

- [ ] **4.1 Advanced AI Features**
  - Implement automatic session title generation after the first few messages.
  - Add "Deep Thinking" mode toggle for non-reasoning models via prompt engineering.
- [ ] **4.2 Voice & Accessibility**
  - Integrate Web Speech API for voice-to-text input.
  - Complete ARIA label coverage and keyboard navigation support (Cmd+K for search, Cmd+N for new chat).
- [ ] **4.3 Performance Optimization**
  - Implement message pagination/lazy loading for long conversation histories.
  - Add local caching for messages and agent configurations to reduce latency.
  - Integrate Token usage statistics and estimated cost display.

---
*Last Updated: 2026-02-01*
