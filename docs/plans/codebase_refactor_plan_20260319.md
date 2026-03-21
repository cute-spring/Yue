# Yue Project Codebase Refactor Plan (2026-03-19)

## **Objective**
The current codebase has several files exceeding 500 lines, with some reaching over 1300 lines. These files violate the **Single Responsibility Principle (SRP)**, making them difficult to maintain, test, and evolve. This plan outlines the strategy to decompose these "God Objects" into modular, manageable components.

---

## **Priority 1: Backend God Objects**

### 1. [chat.py](file://./backend/app/api/chat.py) (~1392 lines)
- **Current Role**: Handles everything related to the `/api/chat` endpoint, including SSE streaming, token management, logging, image handling, and skill routing.
- **Refactor Strategy**:
  - **Move Token Utilities**: Create `backend/app/utils/token_manager.py` for `estimate_tokens` and related constants.
  - **Move Logging Helpers**: Create `backend/app/utils/chat_logger.py` for payload formatting and truncation logic.
  - **Move SSE Logic**: Extract complex SSE generator logic into a dedicated service `backend/app/services/chat/stream_generator.py`.
  - **Modularize Endpoints**: Split into `chat_session.py` (CRUD) and `chat_stream.py` (Execution).

### 2. [doc_retrieval.py](file://./backend/app/services/doc_retrieval.py) (~1324 lines)
- **Current Role**: Path resolution, recursive file walking, content extraction (PDF/Text), and snippet scoring.
- **Refactor Strategy**:
  - **Extract Path Resolver**: Create `backend/app/services/doc/path_resolver.py` for safe path handling and root resolution.
  - **Extract Content Readers**: Create `backend/app/services/doc/readers/` with `pdf_reader.py` and `text_reader.py`.
  - **Extract Search Engine**: Move snippet extraction and scoring to `backend/app/services/doc/search_engine.py`.
  - **Simplify Main Service**: `doc_retrieval.py` should only orchestrate these modules.

### 3. [skill_service.py](file://./backend/app/services/skill_service.py) (~684 lines)
- **Current Role**: Registry, router, policy gate, and multiple adapters.
- **Refactor Strategy**:
  - **Split Registry**: Move registration logic to `backend/app/services/skill/registry.py`.
  - **Split Adapters**: Create `backend/app/services/skill/adapters/` for `MarkdownSkillAdapter` and `LegacyAgentAdapter`.
  - **Split Policy**: Move `SkillPolicyGate` to `backend/app/services/skill/policy.py`.

---

## **Priority 2: Frontend God Components**

### 1. [Settings.tsx](file://./frontend/src/pages/Settings.tsx) (~1285 lines)
- **Current Role**: Manages General, MCP, and LLM settings in one file.
- **Refactor Strategy**:
  - **Component Extraction**: Create `frontend/src/components/settings/` directory.
  - **GeneralTab**: Move general preferences and doc access settings.
  - **McpTab**: Move MCP server configuration, status, and tools view.
  - **LlmTab**: Move LLM provider configuration and custom model management.
  - **Simplify Settings.tsx**: Keep it as a shell for tab navigation and global state orchestration.

### 2. [useChatState.ts](file://./frontend/src/hooks/useChatState.ts) (~767 lines)
- **Current Role**: Giant hook managing message history, streaming state, tool calls, and multi-modal data.
- **Refactor Strategy**:
  - **Sub-hooks Pattern**: Split into `useMessageHistory`, `useStreamingResponse`, and `useToolExecution`.
  - **State Reducer**: Move complex state transitions to a dedicated reducer in `frontend/src/hooks/chat/chatReducer.ts`.

### 3. [MessageItem.tsx](file://./frontend/src/components/MessageItem.tsx) (~730 lines)
- **Current Role**: Renders all types of messages (User, Assistant, Error) and their sub-components (Tool calls, Images, Mermaid).
- **Refactor Strategy**:
  - **Extract Sub-components**: Create `MessageContent`, `MessageHeader`, `ToolCallList`, and `ImageAttachment` as standalone components.

---

## **Implementation Principles**
1. **Backward Compatibility**: Ensure all refactored APIs and hooks maintain current interfaces to avoid breaking downstream components.
2. **Incremental Rollout**: Refactor one file at a time, followed by full regression testing (both Unit and E2E).
3. **Strict Linting**: Enforce line limits (e.g., max 300 lines per file) post-refactor.
4. **Shared Utilities**: Avoid duplicating logic; if a function is used across modules, move it to a dedicated `utils` or `common` service.

## **Execution Roadmap**
- **Phase 1 (Backend)**: Focus on `chat.py` and `doc_retrieval.py`.
- **Phase 2 (Frontend)**: Focus on `Settings.tsx` and `MessageItem.tsx`.
- **Phase 3 (Optimization)**: Focus on `useChatState.ts` and `skill_service.py`.
