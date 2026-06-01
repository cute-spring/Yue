# Yue AI Workbench Opportunity Roadmap

Date: 2026-05-30
Status: Opportunity pool
Owner: Product and engineering planning

## Purpose

This document captures high-value product opportunities for Yue after reviewing the current codebase and comparing the platform direction with the 2026 AI tool market.

The intent is not to commit all items to delivery. It is a decision surface for selecting the next one or two projects that deserve implementation plans.

## Product Thesis

Yue should not compete as another generic chat shell. Its stronger path is to become a trusted AI workbench:

- Sources come in as files, local documents, MCP connectors, and notes.
- Agents understand the task and choose the right tool or skill.
- Tool-backed actions are observable and approval-gated when needed.
- Outputs become durable artifacts, notes, reports, tasks, or reusable runbooks.

The current platform already has meaningful building blocks: chat streaming, multi-model selection, agents, MCP, skill import and preflight, local document tools, PDF and Excel tools, action states, trace inspection, uploads, exports, speech, and session context foundations.

## Market Signals Considered

The current AI product market is converging around these patterns:

- Deep research agents that gather evidence, cite sources, and produce structured reports.
- Notebook-style source workspaces where users upload files and ask grounded questions.
- Agentic coding and task agents that run in the background and report progress.
- MCP and connector ecosystems that make tools and business systems callable.
- Human-in-the-loop action execution for systems such as Jira, Confluence, browsers, and internal apps.
- Reusable skills, templates, and agent presets that package repeatable workflows.

Yue has unusually strong alignment with the connector, skill, trace, and approval parts of this market. The biggest opportunity is to turn those platform capabilities into complete user-facing workflows.

## Current Product Leverage

Yue already has:

- Chat sessions, streaming responses, reasoning display, citations, exports, and history metadata.
- Agent creation, Smart Generate, tool binding, model configuration, and provider management.
- MCP config, templates, reload, tool metadata, and Smart Paste.
- Built-in document, PDF, Excel, PPT, and system tools.
- Skill import, preflight, trust, setup, mount, skill groups, and runtime routing.
- Action states with approval tokens, execution status, observability metadata, and an Intelligence Panel.
- Notebook CRUD and session context infrastructure.

The main gaps are product integration gaps:

- Uploaded non-image files are not yet consistently treated as first-class reasoning sources in chat.
- Notes and memory are present but not yet a polished capture, recall, and governance loop.
- Action approvals are visible inside chat but not centralized as a durable operator workflow.
- Skills and agents exist, but repeatable work is not yet packaged as templates or runbooks.
- Trace and action data exist, but product-level success, latency, and failure metrics are not surfaced.

## Opportunity Scoring Rubric

Score each candidate from 1 to 5:

- User value: How directly this helps a real user complete valuable work.
- Existing leverage: How much of the implementation can reuse existing Yue capabilities.
- Differentiation: How strongly this separates Yue from commodity chat tools.
- Feasibility: Higher means easier to ship safely with the current architecture.

Suggested priority score:

`Priority = User value + Existing leverage + Differentiation + Feasibility`

## Ranked Opportunities

| Rank | Opportunity | User value | Existing leverage | Differentiation | Feasibility | Priority | Recommended stage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Source Workspace | 5 | 4 | 5 | 3 | 17 | P0 |
| 2 | Attachment Understanding and Tool Routing | 5 | 5 | 4 | 3 | 17 | P0 |
| 3 | Deep Research Job Mode | 5 | 4 | 5 | 3 | 17 | P0 |
| 4 | Unified Approval Inbox | 4 | 5 | 5 | 4 | 18 | P0 |
| 5 | Chat-to-Note and Memory Capture | 4 | 4 | 4 | 4 | 16 | P1 |
| 6 | Agent Runbooks | 5 | 4 | 5 | 2 | 16 | P1 |
| 7 | Skill and Agent Template Gallery | 4 | 5 | 4 | 4 | 17 | P1 |
| 8 | Agent Task Board | 4 | 4 | 5 | 3 | 16 | P1 |
| 9 | Agent and Tool Metrics Panel | 4 | 4 | 4 | 4 | 16 | P1 |
| 10 | Memory Cards and Recall Governance | 4 | 3 | 5 | 3 | 15 | P2 |
| 11 | Browser and Web Task Agent | 4 | 3 | 4 | 2 | 13 | P2 |

Note: Unified Approval Inbox has the highest numeric score because Yue already has strong action-state foundations. Source Workspace, Attachment Routing, and Deep Research remain strategic P0 candidates because they define the user-facing product shape.

## Opportunity Cards

### 1. Source Workspace

User scenario:
Users work on a project, research question, client case, sprint, or report. They need one place containing files, chats, notes, outputs, selected agents, and relevant tool actions.

Current Yue foundation:
Chat sessions, file uploads, notebook, local docs access, citations, exports, agents, action states, and trace inspection.

Gap:
The platform has assets and sessions, but no durable project-level container that binds them together.

MVP:
- Create a Workspace entity with name, description, created_at, updated_at, default_agent_id, and optional doc roots.
- Allow chats, uploaded files, notes, and generated artifacts to attach to a workspace.
- Add a workspace switcher or workspace field in chat history.
- Use the active workspace as context for source selection and output organization.

Risks:
Data model scope creep. Keep MVP thin and avoid building a full project management system.

Why high ROI:
It organizes existing capabilities into a product users can understand and return to.

### 2. Attachment Understanding and Tool Routing

User scenario:
Users drag in a PDF, Excel file, CSV, image, or mixed bundle and expect Yue to know how to inspect it.

Current Yue foundation:
Upload policy, file storage, PDF tools, Excel tools, built-in agents, citations, vision capability checks, and tool metadata.

Gap:
Uploaded files are persisted and sent with chat requests, but non-image files are not consistently converted into source-aware tool usage.

MVP:
- Detect attachment types after upload.
- Surface suggested agents or skills: PDF Researcher, Excel Analyst, Docs Assistant, PPT Builder.
- Inject attachment metadata into prompt context.
- For supported documents, make tools resolve uploaded file paths directly.
- Show a small source strip in the composer or assistant response.

Risks:
Path resolution, security policy, and file lifecycle must be clear. Avoid giving tools arbitrary filesystem paths without doc access checks.

Why high ROI:
This turns the existing upload and built-in tool work into a visible user win.

### 3. Deep Research Job Mode

User scenario:
Users want Yue to read sources, inspect evidence, cite claims, and produce a structured report or briefing.

Current Yue foundation:
Docs search/read, PDF tools, citations, trace, exports, long responses, agents, and model routing.

Gap:
Research happens inside normal chat instead of a task mode with source selection, progress, and durable output.

MVP:
- Add a research job form: question, sources, output type, citation requirement, max depth.
- Run the job as a chat-backed task using selected source tools.
- Persist a research artifact with summary, findings, citations, and export links.
- Show progress states and trace summary.

Risks:
Long-running task orchestration may need cancellation and retry handling. Scope the first version to local sources.

Why high ROI:
It maps directly to one of the strongest market use cases and reuses Yue's document stack.

### 4. Unified Approval Inbox

User scenario:
Users and operators need a single place to review pending tool-backed actions before they affect Jira, Confluence, files, or other systems.

Current Yue foundation:
Action states, approval tokens, lifecycle transitions, Intelligence Panel approval buttons, and trace payloads.

Gap:
Approvals are chat-local and not yet surfaced as an operator queue.

MVP:
- Add an Approval Inbox page with filters for awaiting approval, failed, succeeded, rejected.
- Show action name, source chat, arguments, reason, risk, timestamps, and latest status.
- Allow approve/reject for pending actions.
- Link back to the originating chat and trace.

Risks:
Must preserve the existing approval-token semantics and avoid duplicate execution.

Why high ROI:
This is a trust layer. It turns Yue from a smart assistant into an operable agent platform.

### 5. Chat-to-Note and Memory Capture

User scenario:
Users want to preserve useful answers, decisions, preferences, and project facts without manually copying text.

Current Yue foundation:
Notebook CRUD, chat summaries, tags, session context service, and message actions.

Gap:
The note capture loop is not yet a reliable product feature. Memory infrastructure is present but not obvious to users.

MVP:
- Make save-to-note actually create a note from selected assistant/user content.
- Auto-generate title, summary, tags, and source chat backlink.
- Allow "remember this" for durable user/project facts with review.
- Show captured notes in workspace or chat context.

Risks:
Memory write quality and privacy controls need visible user control.

Why high ROI:
It makes Yue better the longer someone uses it.

### 6. Agent Runbooks

User scenario:
Users repeat the same multi-step workflows: sprint report, document QA, weekly research, release notes, Jira cleanup, or Confluence scaffolding.

Current Yue foundation:
Agents, skills, MCP tools, action preflight, approvals, trace, and exports.

Gap:
Successful workflows cannot yet be saved and rerun as structured recipes.

MVP:
- Let users save a chat workflow as a runbook template.
- Store runbook name, goal, default agent, required inputs, source selection, and approval policy.
- Allow manual run with previewed steps.

Risks:
Automatic workflow extraction can be brittle. Start with manual templates.

Why high ROI:
It moves Yue from one-off answers to repeatable operations.

### 7. Skill and Agent Template Gallery

User scenario:
Users want useful agents immediately, without configuring prompts, tools, and policies from scratch.

Current Yue foundation:
Built-in agents, Smart Generate, Skill Groups, Skill Import, Preflight, Setup, and Mount.

Gap:
The platform can host capabilities, but discovery and onboarding still feel admin-heavy.

MVP:
- Add a gallery of templates: PR Reviewer, PDF Researcher, Excel Analyst, Sprint Health, Weekly Report, Translator, PPT Builder.
- Each template shows purpose, required tools, risk, setup state, and one-click install or enable.
- Include a one-shot test prompt.

Risks:
Template maintenance. Keep templates versioned and linked to skills.

Why high ROI:
It converts platform flexibility into fast time-to-value.

### 8. Agent Task Board

User scenario:
Users delegate multi-step work and want to see queued, running, blocked, approval-needed, done, and failed states.

Current Yue foundation:
Action states, trace, chat sessions, status metadata, and long-running stream structure.

Gap:
Tasks are embedded in chats, not visible as work items.

MVP:
- Add a task board backed by chat runs or explicit job records.
- Show status, owner agent, model, source workspace, latest event, and next action.
- Link each task to its chat and output artifact.

Risks:
Job model may overlap with Deep Research and Runbooks. Define a minimal shared task abstraction.

Why high ROI:
It supports the market shift from chat to delegated work.

### 9. Agent and Tool Metrics Panel

User scenario:
Admins and builders want to know which agents work, which tools fail, and where latency/cost comes from.

Current Yue foundation:
Trace events, action events, skill effectiveness report endpoint, usage metadata, and health monitor.

Gap:
Operational quality data exists but is not yet a product surface.

MVP:
- Show success rate, average duration, failure count, approval rate, top failed tools, and recent errors by agent/tool.
- Start with local last-24h and last-7d views.
- Add links to trace bundles.

Risks:
Metrics definitions must be stable enough for users to trust.

Why high ROI:
It makes Yue easier to operate and debug as the tool ecosystem grows.

### 10. Memory Cards and Recall Governance

User scenario:
Users want Yue to remember preferences and project facts, while being able to inspect, edit, and forget them.

Current Yue foundation:
Session context manager integration, retrieval boundaries, summaries, and memory animation demo.

Gap:
Memory is not yet exposed as a governed product feature.

MVP:
- Show memory cards grouped by user preference, project fact, decision, and recurring instruction.
- Allow approve, edit, disable, or delete.
- Show when a response used recalled memory.

Risks:
Memory quality and privacy sensitivity. Make all persistent memory explicit at first.

Why high ROI:
It creates long-term personalization while keeping trust.

### 11. Browser and Web Task Agent

User scenario:
Users want Yue to inspect or operate web apps, especially internal systems that lack clean APIs.

Current Yue foundation:
MCP, action approvals, agents, tool risk classification, and trace.

Gap:
There is no dedicated browser task workflow.

MVP:
- Start with read and draft actions, not direct uncontrolled submission.
- Generate form-fill or update previews.
- Require approval before write actions.

Risks:
Browser automation is fragile and high-risk. It should follow approval and trace maturity.

Why high ROI:
High market interest, but best treated as a later layer once trust workflows are strong.

## Recommended Selection Path

The next product decision should choose one of these two tracks.

Track A: Source-first workbench

- Source Workspace
- Attachment Understanding and Tool Routing
- Deep Research Job Mode

Choose this if the immediate goal is user-facing productivity and clearer product identity.

Track B: Trust-first agent operations

- Unified Approval Inbox
- Agent Runbooks
- Agent and Tool Metrics Panel

Choose this if the immediate goal is credible agent execution, internal operations, and platform maturity.

Recommended default:

Start with Track A, but pull in Unified Approval Inbox as soon as actions become central to the selected workflow.

## Suggested Next Implementation Plans

Write one dedicated execution plan for the first selected P0 item:

- `docs/plans/2026-05-30-source-workspace-implementation-plan.md`
- `docs/plans/2026-05-30-attachment-understanding-tool-routing-plan.md`
- `docs/plans/2026-05-30-deep-research-job-mode-plan.md`
- `docs/plans/2026-05-30-unified-approval-inbox-plan.md`

Each execution plan should include:

- Problem statement
- User scenarios
- Current code references
- MVP scope
- Explicit non-goals
- Data model changes
- Backend API changes
- Frontend UX changes
- Testing plan
- Release and rollback notes
- Open questions

## First Pick Recommendation

If choosing only one, start with Attachment Understanding and Tool Routing.

Reason:
It is the smallest feature that makes many existing Yue investments visible. It improves chat, files, PDF, Excel, agents, citations, and source trust without first requiring a full workspace model.

If choosing a more strategic foundation, start with Source Workspace.

Reason:
It creates a durable container for the next several product bets, including research jobs, notes, outputs, and runbooks.

