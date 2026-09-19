# Minimal Learning Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a prompt-only Learning Coach available through Yue's existing built-in Agent and Skill catalogs.

**Architecture:** The existing catalog discovers a new YAML Agent definition and the existing skill runtime discovers a Markdown package. The Learning Coach has no tools, no storage, and no frontend changes; its behavior is wholly in its two prompt files.

**Tech Stack:** Python/Pytest catalog and skill-registry tests; YAML built-in Agent definitions; Markdown skill packages.

---

### Task 1: Make the Learning Coach skill discoverable

**Files:**
- Create: `backend/data/skills/learning-coach/SKILL.md`
- Test: `backend/tests/test_learning_coach_skill.py`

- [ ] **Step 1: Write the failing skill-discovery test**

```python
from pathlib import Path

from app.services.skills.registry import SkillRegistry


def test_learning_coach_skill_loads_from_builtin_skill_directory():
    builtin_skills_dir = Path(__file__).resolve().parents[1] / "data" / "skills"
    registry = SkillRegistry(skill_dirs=[str(builtin_skills_dir)])
    registry.load_all()

    skill = registry.get_full_skill("learning-coach", "1.0.0")

    assert skill is not None
    assert skill.name == "learning-coach"
    assert skill.version == "1.0.0"
    assert "Socratic" in skill.system_prompt
    assert "L0" in skill.system_prompt
    assert "L6" in skill.system_prompt
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_learning_coach_skill.py -q`

Expected: FAIL because `learning-coach` is absent.

- [ ] **Step 3: Create the smallest valid skill package**

Create `backend/data/skills/learning-coach/SKILL.md` with frontmatter naming version `1.0.0`, `entrypoint: system_prompt`, and a System Prompt that requires goal-directed technical learning, Socratic questions, hints and retries, Feynman explanations, project-relevant applications, and conversational L0–L6 guidance. Explicitly prohibit exhaustive maps, percentage progress, persistent scores, automatic material discovery, citations, tools, review scheduling, and claims that assessment continues beyond the chat.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_learning_coach_skill.py -q`

Expected: PASS.

### Task 2: Register Learning Coach as a built-in Agent

**Files:**
- Create: `backend/data/builtin/agents/builtin-learning-coach.yaml`
- Modify: `backend/app/services/builtin_agent_catalog.py`
- Modify: `backend/tests/test_builtin_agent_catalog.py`
- Create: `backend/tests/test_builtin_learning_coach_agent.py`

- [ ] **Step 1: Write failing catalog and Agent configuration tests**

Add `"builtin-learning-coach"` to the expected ID set in `test_builtin_agent_catalog_loads_default_agents`. Create `test_builtin_learning_coach_agent.py` asserting that `AgentStore` loads the Agent with `skill_mode == "manual"`, `visible_skills == ["learning-coach:1.0.0"]`, `enabled_tools == []`, `require_citations is False`, and a prompt that identifies it as a Learning Coach.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_builtin_agent_catalog.py tests/test_builtin_learning_coach_agent.py -q`

Expected: FAIL because the catalog does not include Learning Coach.

- [ ] **Step 3: Add the minimal Agent configuration**

Create `builtin-learning-coach.yaml` following existing no-tool built-in Agent YAMLs. Set `id: builtin-learning-coach`, `name: Learning Coach`, a concise role prompt, `skill_mode: manual`, `visible_skills: [learning-coach:1.0.0]`, `enabled_tools: []`, `require_citations: false`, and the standard built-in Agent fields. Add `builtin-learning-coach` after `builtin-architect` in `_DEFAULT_ID_ORDER`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_builtin_agent_catalog.py tests/test_builtin_learning_coach_agent.py -q`

Expected: PASS.

### Task 3: Validate the focused feature slice

**Files:**
- Modify: none unless a preceding focused test identifies a compatibility issue.

- [ ] **Step 1: Run all affected backend tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_learning_coach_skill.py tests/test_builtin_agent_catalog.py tests/test_builtin_learning_coach_agent.py tests/test_skill_foundation_unit.py -q`

Expected: PASS.

- [ ] **Step 2: Inspect the diff against the design**

Run: `git diff --check HEAD~1..HEAD && git status --short`

Expected: no whitespace errors; only Learning Coach code, tests, and the implementation-plan documents are changed.

## Plan Self-Review

- Scope coverage: Tasks 1–2 deliver the only approved surfaces: a prompt-only skill and an Agent exposing it. Task 3 verifies the affected registration and parser paths.
- No hidden persistence or UI work: no migration, API, frontend, Workspace, Memory, tool, citation, or scheduler file appears in the plan.
- Test coverage: the new skill is loaded by the real registry and the Agent is loaded through the real built-in AgentStore path.
