# Yue

Yue is an AI chat-agent platform that combines provider-backed agents, MCP tools, skills, and streaming chat into one user-facing runtime.

## Language

**Chat execution boundary**:
The backend boundary that converts an incoming chat request into provider execution, tool activity, streamed events, and persisted chat state.
_Avoid_: Chat pipeline, agent loop

**Provider adapter**:
The Yue-owned component that configures a specific LLM provider or OpenAI-compatible endpoint for the chat execution boundary.
_Avoid_: Model factory, LLM client

**Tool runtime**:
The Yue-owned layer that discovers, authorizes, schemas, and executes builtin and MCP tools for an agent run.
_Avoid_: MCP layer, tool registry

**Migration compatibility stage**:
The interim release on the previous major Pydantic AI line used to expose and resolve deprecations before the V2 upgrade.
_Avoid_: Partial upgrade, temporary version

**OpenAI execution protocol**:
The API semantics used by Yue provider adapters when executing an OpenAI-compatible chat request. Existing adapters preserve Chat Completions behavior during the Pydantic AI V2 migration.
_Avoid_: OpenAI model name, provider transport

**Provider HTTP boundary**:
The boundary at which a Yue provider adapter supplies an HTTP client required by a provider SDK or Pydantic AI. Pydantic AI V2-specific `httpx2` use remains confined here.
_Avoid_: Global HTTP migration, shared HTTP stack

**Usage contract**:
The Yue-facing token and completion metrics exposed by chat execution and persistence. It keeps `prompt_tokens` and `completion_tokens` stable while framework-specific usage fields are translated internally.
_Avoid_: Provider usage object, raw telemetry fields

**Side-effecting tool policy**:
The rule governing function tools that can change user-visible or external state. An agent combining them with structured output must declare its output-completion behavior explicitly.
_Avoid_: Default tool behavior, implicit tool ordering

**Tool runtime**:
The Yue-owned component that discovers, authorizes, schemas, and executes builtin and MCP tools for the chat execution boundary. It remains the integration seam during the Pydantic AI V2 migration.
_Avoid_: Pydantic AI MCPToolset, framework tool layer

**Migration release gate**:
The required evidence before a framework migration reaches production: offline regression coverage, credentialed staging smoke tests, and monitored canary rollout with rollback thresholds.
_Avoid_: Single test-suite pass, direct production upgrade

**Workspace**:
A project workbench where a user gathers materials, advances chats, preserves intermediate notes, reviews durable memory, and returns to concrete next work. It is not merely a file folder, chat filter, or retrieval container.
_Avoid_: Workspace as a passive folder, workspace as only a chat history filter, workspace as only RAG configuration

**Yue Understanding**:
The product promise that Yue becomes more useful as it accumulates reviewed understanding about the user and the active project context. It has two layers: User Memory and Workspace Memory.
_Avoid_: Memory as only chat history, memory as unreviewed transcript accumulation

**User Memory**:
Durable understanding that applies across workspaces, such as the user's language preference, collaboration style, recurring technical preferences, and stable personal workflow constraints.
_Avoid_: Project-specific facts, one-off task state

**Workspace Memory**:
Durable understanding that applies only inside one Workspace, such as project facts, decisions, terminology, constraints, recurring instructions, and unresolved questions for that project workbench.
_Avoid_: Global user preferences, raw notes, unreviewed assistant claims

**Workspace Understanding**:
Yue's current, user-reviewable understanding of a sustained area of work inside a Workspace. It should be useful beyond IT projects and can cover any ongoing domain such as software, research, travel, writing, renovation, investing, health goals, or family planning.
_Avoid_: Project-only terminology, source-list-first workspace design, treating Workspace as only a technical/RAG feature

**Workspace Understanding Group**:
A plain-language category used to present Workspace Understanding. The default groups are Background, Goals, Decisions, Constraints, Preferences, Terms, Open Questions, and Current State.
_Avoid_: Engineering-only labels such as Project Facts as the primary universal grouping

**Workspace Understanding Presentation**:
Workspace Understanding should use a simple, predictable grouping model rather than scenario-adaptive layouts. Keep the same plain-language groups visible or consistently ordered so users can quickly build trust in where background, goals, constraints, decisions, preferences, terms, open questions, and current state live.
_Avoid_: Workspace-type-specific adaptive grouping, hiding the information architecture behind inference

**Workspace Understanding Summary**:
The first screen for a Workspace should summarize each Workspace Understanding Group with counts, one or two representative items, and a review/manage action instead of showing full resource or memory lists by default.
_Avoid_: Full-list-first workspace screens, forcing users to inspect Sources, Notes, Memory, and Artifacts before seeing what Yue understands

**Applied User Memory Preview**:
A lightweight preview inside a Workspace showing the most relevant User Memory currently influencing the conversation. It should make cross-workspace preferences visible without mixing them into Workspace Memory.
_Avoid_: Duplicating User Memory into every Workspace, hiding user-level preferences that affect workspace answers

**Memory Candidate**:
A Yue-detected piece of understanding that may be worth saving as User Memory or Workspace Memory. When a user explicitly states a preference, habit, interest, style, project constraint, or durable decision in conversation, Yue should analyze it immediately and ask for lightweight confirmation before it becomes durable memory.
_Avoid_: Silent durable memory writes, burying memory capture only in a settings or management page

**Inline Memory Confirmation**:
A non-blocking confirmation shown in conversation after Yue detects a Memory Candidate. It summarizes the proposed memory in plain language and lets the user save it, keep it for the current turn only, or edit it before saving.
_Avoid_: Modal-first memory capture, interrupting the user's current task, exposing raw memory JSON as the confirmation UI

**Memory Scope Recommendation**:
Yue should classify each Memory Candidate as likely User Memory, Workspace Memory, or current-turn-only context before asking for confirmation. The confirmation UI should expose the recommended destination while allowing the user to switch it.
_Avoid_: Asking the user to classify every memory from scratch, saving project-specific facts as global User Memory

**High-Signal Memory Capture**:
Yue should proactively suggest memory only when the user provides high-signal durable information, such as explicit defaults or preferences, corrections to Yue's understanding, clear decisions, term definitions, or long-lived constraints.
_Avoid_: Prompting on ordinary chat content, saving assistant-only inferences as durable memory, noisy memory prompts every few turns

**Conversation-First Memory Correction**:
When a user corrects Yue in conversation, Yue should treat the correction as a Memory Candidate and propose updating, replacing, or archiving the affected User Memory or Workspace Memory inline. Workspace management screens should support review and cleanup, but they should not be the only way to fix stale or wrong memory.
_Avoid_: Forcing users to manually hunt through memory management screens after correcting Yue in chat, silently keeping contradicted durable memory active
