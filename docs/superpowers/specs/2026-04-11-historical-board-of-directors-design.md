# Historical Board of Directors (跨时空董事会) - Design Spec

## 1. Overview
The upgraded "Historical Board of Directors" is not only a persona simulation skill, but a **deep methodology advisor**. Its purpose is to help users think through work, life, and long-horizon decisions by borrowing the worldview, life trajectory, and decision patterns of historical figures.

This version shifts from "roleplay-first" to **analysis-first, persona-second**. The skill should first identify the user's core problem, then choose a best-fit primary mentor, and finally assemble a supporting roundtable to expand, challenge, or correct that primary perspective.

The extensibility model remains unchanged at the architectural level: the skill logic stays in `SKILL.md`, routing metadata stays in `index.md`, and each persona remains independently defined in `profiles/*.md`. The key upgrade is that persona files become significantly deeper and more structured.

## 2. Architecture & File Structure

The upgraded skill continues to live under the existing skill directory:

```text
historical-board-of-directors/
├── SKILL.md                 # Core orchestration prompt and deep-analysis protocol
├── index.md                 # Persona routing table, match tags, fit and caution metadata
└── profiles/                # Independent persona modules
    ├── steve_jobs.md
    ├── sun_tzu.md
    └── marcus_aurelius.md
```

## 3. Design Goals

### 3.1 Primary Goals
1. Produce deeper insight than ordinary roleplay.
2. Make each persona feel grounded in a life trajectory, not just a speaking style.
3. Help the user act on real problems in work, relationships, meaning, discipline, leadership, and strategy.
4. Preserve easy extensibility for future historical figures through standalone Markdown files.

### 3.2 Non-Goals
1. Build a fully automated retrieval system outside the skill framework.
2. Guarantee academic or historiographical completeness for every figure.
3. Add scripts or new runtime code for persona inference in this iteration.

## 4. Output Model

The default output model will be **"Primary Mentor First, Roundtable Second"**:

1. The skill chooses **one primary mentor** whose methodology best fits the user's problem.
2. The skill chooses **two supporting voices** that either complement or challenge the main view.
3. The primary mentor provides a deep analysis of the user's situation.
4. The supporting voices respond with alternative emphasis, critique, or expansion.
5. The skill concludes with an executive synthesis that translates the historical perspectives into modern, actionable advice.

This structure preserves depth while keeping the multi-perspective value of the original concept.

## 5. Component Design

### 5.1 `SKILL.md` (Deep Methodology Orchestrator)
The new orchestrator prompt should enforce a strict analysis protocol before role simulation.

#### Required internal workflow
1. **Problem Classification**
   - Identify problem domain: work, strategy, life direction, emotional regulation, leadership, conflict, relationships, etc.
   - Identify urgency, emotional intensity, and whether the user needs diagnosis, decision support, or direct coaching.

2. **Core Tension Extraction**
   - Reduce the user's question to its underlying tension.
   - Example tensions: speed vs quality, ambition vs peace, control vs acceptance, confrontation vs indirection, self-expression vs duty.

3. **Primary Mentor Selection**
   - Choose one best-fit persona from `index.md`.
   - The selection must consider both fit and caution metadata, not only domain tags.

4. **Supporting Voices Selection**
   - Choose two additional personas that either:
     - broaden the analysis,
     - challenge the primary mentor's bias,
     - or offer a different level of abstraction.

5. **Profile Loading**
   - Read the selected persona files with `builtin:docs_read` before generating any advice.

6. **Deep Response Protocol**
   - First output a short diagnosis of the user's underlying problem.
   - Then let the primary mentor provide a deep methodology-based response.
   - Then let the two supporting voices provide correction or reinforcement.
   - End with a synthesis, practical steps, and risk notes.

### 5.2 `index.md` (Routing Table)
`index.md` must evolve from a lightweight tag list into a routing-oriented registry.

Each persona entry should include:
- File path
- Core domains
- Best-fit tensions
- Typical use cases
- Caution flags
- Style intensity

This allows the orchestrator to make better selections, such as distinguishing:
- a strategic conflict from an existential one,
- a product decision from a meaning crisis,
- or a discipline problem from an interpersonal wound.

### 5.3 `profiles/*.md` (Deep Persona Modules)
Persona files should become deeper and more operational. Each file should follow a standardized schema:

- **Positioning**: one-sentence summary of what this figure is best used for.
- **Core Worldview (核心世界观)**: how the figure interprets life, order, conflict, truth, progress, or duty.
- **Life Trajectory (人生动线)**: the figure's formative experiences, major transitions, and mature phase.
- **Canonical Tensions (核心矛盾)**: the enduring tensions that shaped their life and thought.
- **Decision Framework (决策框架)**: how they evaluate situations and choose actions.
- **Operating Principles (长期方法论)**: repeatable principles they would apply across multiple contexts.
- **Canonical Cases (关键案例锚点)**: 3-5 historical or biographical anchor cases.
- **Advice Style (建议风格)**: how they would guide the user.
- **Blind Spots (盲区与代价)**: what this figure tends to underweight, overdo, or misjudge.
- **Applicable Scenarios (适用场景)**: what kinds of user problems this persona is especially useful for.
- **Non-Applicable Scenarios (慎用场景)**: what kinds of user problems this persona is not suited to handle as the main mentor.
- **Key Quotes (代表性语录)**: style anchors for tone and vocabulary.

## 6. Response Protocol

The final answer should follow a fixed high-depth structure:

1. **问题本质**
   - Summarize the user's real dilemma in one concise paragraph.

2. **主导师深剖**
   - Explain how the primary mentor defines the problem.
   - Explain which variables they care about first.
   - Explain what they would advise the user to do.
   - Explain why this advice follows from their life trajectory and long-term methodology.
   - Explain the likely costs or tradeoffs.

3. **补充视角一**
   - Provide a distinct expansion, correction, or challenge.

4. **补充视角二**
   - Provide a second distinct expansion, correction, or challenge.

5. **综合行动建议**
   - Translate the historical discussion into a modern action plan.

6. **风险与适用边界**
   - Clarify where this set of advice applies well and where the user should be cautious.

## 7. Example Experience

### Example Input
"My team keeps pushing to ship fast, but I believe the product is not ready. I am exhausted, and I also wonder whether I even want to keep doing this kind of work."

### Expected behavior
1. Detect that this is not only a product conflict, but also a meaning and burnout problem.
2. Select Steve Jobs as a possible primary mentor for product standards, or Marcus Aurelius if the emotional-regulation and duty layer is dominant.
3. Use Sun Tzu as a strategic supplement if timing and leverage matter.
4. Produce a response that addresses both execution and inner orientation, rather than giving shallow product advice only.

## 8. Extensibility

The extensibility principle remains intentionally simple:
1. Add a new persona file under `profiles/`.
2. Register it in `index.md` with richer routing metadata.

No changes to core orchestration logic should be required when introducing new figures, as long as the new profile follows the upgraded schema.

## 9. Constraints & Requirements

1. The skill MUST continue to use `builtin:docs_read` to load persona profiles dynamically at runtime.
2. The prompt MUST instruct the model to reason from the persona's worldview and life trajectory, not merely imitate speech patterns.
3. The prompt MUST require fit checking and caution checking before selecting a primary mentor.
4. The prompt MUST prevent shallow "quote-and-vibes" answers.
5. The final response MUST remain in the user's language.
