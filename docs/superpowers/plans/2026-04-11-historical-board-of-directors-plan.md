# Historical Board of Directors Deep Advisor Upgrade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing skill from a lightweight persona roundtable into a deep methodology advisor that analyzes the user's underlying dilemma, selects a primary mentor, and delivers grounded guidance from richer historical profiles.

**Architecture:** Keep the same pluggable file layout, but deepen each layer. `SKILL.md` becomes an analysis-first orchestrator with a fixed deep-response protocol. `index.md` becomes a routing table that supports primary-mentor selection and caution-aware matching. Each `profiles/*.md` file becomes a richer methodology document with life trajectory, canonical cases, operating principles, and applicability boundaries.

**Tech Stack:** Trae Skill framework (Markdown-based prompts, `builtin:docs_read` tool).

---

## Chunk 1: Routing and Orchestration

### Task 1: Rewrite the routing registry

**Files:**
- Modify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/index.md`

- [ ] **Step 1: Rewrite the registry into a routing table**

Replace the current tag-only list with a structured registry that includes:
- file path
- primary domains
- best-fit tensions
- typical use cases
- caution flags
- style intensity

The content should remain Markdown-only and easy for future manual extension.

- [ ] **Step 2: Verify the registry reflects all three personas**

Read: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/index.md`
Expected: Entries exist for Steve Jobs, Sun Tzu, and Marcus Aurelius with richer routing metadata.

### Task 2: Rewrite the main orchestrator prompt

**Files:**
- Modify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/SKILL.md`

- [ ] **Step 1: Rewrite the description and system prompt**

Update `SKILL.md` so it:
- uses "analysis first, persona second"
- selects one primary mentor and two supporting voices by default
- extracts the user's core tension before any role simulation
- requires profile loading before advice
- forces a deep response structure:
  - 问题本质
  - 主导师深剖
  - 补充视角一
  - 补充视角二
  - 综合行动建议
  - 风险与适用边界
- prevents shallow quote-driven answers
- instructs the model to reason from life trajectory and operating principles, not just tone

- [ ] **Step 2: Re-read the updated file**

Read: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/SKILL.md`
Expected: Prompt clearly describes primary-mentor-first routing and the fixed deep-response protocol.

## Chunk 2: Deep Persona Modules

### Task 3: Upgrade Steve Jobs profile

**Files:**
- Modify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/steve_jobs.md`

- [ ] **Step 1: Rewrite Steve Jobs as a deep methodology profile**

Add these sections:
- Positioning
- Core Worldview
- Life Trajectory
- Canonical Tensions
- Decision Framework
- Operating Principles
- Canonical Cases
- Advice Style
- Blind Spots
- Applicable Scenarios
- Non-Applicable Scenarios
- Key Quotes

Make the content useful for product, standards, focus, and high-agency execution problems without reducing the persona to attitude only.

- [ ] **Step 2: Re-read the file**

Read: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/steve_jobs.md`
Expected: The file uses the richer schema and includes fit plus blind spots.

### Task 4: Upgrade Sun Tzu profile

**Files:**
- Modify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/sun_tzu.md`

- [ ] **Step 1: Rewrite Sun Tzu as a deep methodology profile**

Use the same section structure. Emphasize:
- calculation before action
- shaping conditions instead of forcing outcomes
- indirectness, positioning, timing, leverage
- where Sun Tzu should not be the main mentor, especially emotionally intimate questions

- [ ] **Step 2: Re-read the file**

Read: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/sun_tzu.md`
Expected: The file uses the richer schema and clearly names both strengths and boundaries.

### Task 5: Upgrade Marcus Aurelius profile

**Files:**
- Modify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/marcus_aurelius.md`

- [ ] **Step 1: Rewrite Marcus Aurelius as a deep methodology profile**

Use the same section structure. Emphasize:
- control vs non-control
- duty, inner order, disciplined self-governance
- emotional steadiness under pressure
- where Stoic framing can become over-detached

- [ ] **Step 2: Re-read the file**

Read: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/marcus_aurelius.md`
Expected: The file uses the richer schema and clearly names both strengths and boundaries.

## Chunk 3: Verification

### Task 6: Validate the resulting skill package

**Files:**
- Verify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/SKILL.md`
- Verify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/index.md`
- Verify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/steve_jobs.md`
- Verify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/sun_tzu.md`
- Verify: `/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/profiles/marcus_aurelius.md`

- [ ] **Step 1: List the skill directory**

Run: `ls -R /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/`
Expected: The same five files exist and no extra runtime files were introduced.

- [ ] **Step 2: Run diagnostics on touched Markdown files**

Use `GetDiagnostics` on:
- `file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/SKILL.md`
- `file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/historical-board-of-directors/index.md`
- each upgraded profile file

Expected: No editor diagnostics.

- [ ] **Step 3: Review git diff for scope control**

Run: `git diff -- backend/data/skills/historical-board-of-directors`
Expected: Diff only contains the intended prompt and content upgrades.

- [ ] **Step 4: Do not commit unless explicitly requested**

Leave the branch changes uncommitted until the human asks for a commit. This repo already contains unrelated in-flight work, so scope discipline matters.
