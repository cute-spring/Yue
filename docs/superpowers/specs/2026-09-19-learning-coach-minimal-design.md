# Minimal Learning Coach Design

## Goal

Expose an optional Learning Coach through Yue's existing built-in Agent and Skill catalogs. It guides a technical or AI-tool learner within the current chat without introducing a learning platform or any new durable state.

## Approach

Add a prompt-only `learning-coach` built-in skill and a `builtin-learning-coach` Agent that manually exposes it. Both use the established YAML/Markdown catalog formats and no tools. The Agent's prompt gives the teaching role; the skill supplies the repeatable learning loop and L0–L6 feedback rubric when the user activates it.

The model's knowledge is the default source. User-named material may be used only as current-chat context; the feature does not discover materials, create citations, or retain material metadata. Chat history remains the only learning history, so existing chat deletion removes it naturally.

## Explicitly Out of Scope

- New tables, migrations, APIs, persistent learner profiles, Workspace Memory writes, or cross-chat continuity.
- Learning dashboards, progress cards, reminders, review queues, source selectors, citations, and source snapshots.
- Separate assessment calls, grading services, code execution, tool access, or frontend controls.
- Any behavior change to the default agent or ordinary chat.

## Teaching Behavior

The Learning Coach first asks only for the learner's goal and current level when either is needed; otherwise it states a reasonable assumption and proceeds. It builds a small goal-directed path, not an exhaustive knowledge tree. Each round uses one appropriate technique: Socratic question, concise hint and retry, Feynman explanation, or a project-relevant application prompt.

Feedback may state a lightweight current L0–L6 judgment: unknown, recognition, recall, explanation, application, transfer, and teach/critique. The wording must make clear that this is conversational guidance for the current chat, not a permanent, precise, or saved score. It must avoid repeated dashboards, complete trees, and percentage progress claims.

## Files and Tests

- Create `backend/data/skills/learning-coach/SKILL.md` using the repository's prompt-skill frontmatter format.
- Create `backend/data/builtin/agents/builtin-learning-coach.yaml`, referencing `learning-coach:1.0.0` with manual skill mode and no tools.
- Update `backend/app/services/builtin_agent_catalog.py` so Learning Coach has a stable built-in display position.
- Extend `backend/tests/test_builtin_agent_catalog.py` to require the new built-in Agent and verify its prompt-facing configuration.
- Add a narrow skill-registry test that loads the real built-in skill and asserts its name, version, and teaching instructions are available.

## Error Handling and Compatibility

The implementation relies on existing catalog validation and skill parsing. If the Skill cannot load, the existing preflight/runtime behavior handles it; no new fallback path is required. Existing Agent and Skill definitions remain unchanged.
