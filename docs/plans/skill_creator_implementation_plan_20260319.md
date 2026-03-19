# Skill-Creator Implementation Plan (2026-03-19)

## **Objective**
Introduce the `skill-creator` skill to the Yue project to enable an AI-driven "Define -> Build -> Eval -> Iterate" loop for new skill development. This plan bridges the gap between our current skill architecture and the advanced iterative capabilities of the Anthropics `skill-creator`.

---

## **1. Core Components & Gaps**

### **1.1 The Skill Itself: `skill-creator.md`**
- **Goal**: Port the high-level logic from Anthropics but adapt it to Yue's three-layer directory structure and `SKILL.md` format.
- **Location**: `backend/data/skills/skill-creator.md` (Built-in layer).

### **1.2 Missing Tools (The Gaps)**
- **`SkillBenchmarkTool`**: A new built-in tool that allows the AI to run a batch of prompts against a specific skill version and collect outputs.
- **`SkillEvolutionTool`**: A tool to compare two skill versions or suggest description improvements based on trigger success rates.

---

## **2. Implementation Roadmap**

### **Phase 1: Foundation (The Skill Definition)**
- [ ] Create `backend/data/skills/skill-creator.md`.
- [ ] Define Frontmatter:
  ```yaml
  name: skill-creator
  version: 1.0.0
  description: Create, modify, and optimize skills. Use when users want to build new workflows or refine existing skill triggering and performance.
  capabilities: [skill-engineering, iterative-refinement]
  entrypoint: system_prompt
  constraints:
    allowed_tools: [builtin:docs_read, builtin:docs_write, builtin:skill_benchmark]
  ```
- [ ] Port `System Prompt` and `Instructions` with Yue-specific path knowledge (e.g., `data/skills` vs `~/.yue/skills`).

### **Phase 2: The Benchmark Engine (Backend Enhancement)**
- [ ] **Implement `SkillBenchmarkTool`**:
  - Add to `backend/app/mcp/builtin/system.py` or a new `skill_tools.py`.
  - Input: `skill_name`, `version`, `test_prompts` (List).
  - Logic: Mock a chat session with the target skill active, run the prompts, and return a JSON summary of responses.
- [ ] **Expose Skill Effectiveness Data**:
  - Update `skill_service.py` to allow `skill-creator` to read `skill_effectiveness` logs for data-driven optimization.

### **Phase 3: Integration & UX**
- [ ] **Frontend Indicators**:
  - Add a "Create Skill" shortcut in the UI that triggers the `skill-creator` skill.
- [ ] **Verification**:
  - Use `skill-creator` to create a simple new skill (e.g., `git-helper`) and verify the hot-reload and benchmark flow.

---

## **3. Success Criteria**
1. AI can autonomously draft a valid `SKILL.md` file in the correct directory.
2. AI can run a "Vibe Check" or "Benchmark" and report if the new skill is performing as expected.
3. System identifies and resolves conflicts if a new skill overlaps with existing ones.

---

## **4. File-level Changes Design**

| File Path | Action | Description |
| :--- | :--- | :--- |
| `backend/data/skills/skill-creator.md` | Create | The core skill logic. |
| `backend/app/mcp/builtin/skill_tools.py` | Create | Implementation of `SkillBenchmarkTool`. |
| `backend/app/mcp/registry.py` | Modify | Register the new skill-related tools. |
| `backend/app/services/skill_service.py` | Modify | Add helper methods for bench-marking (mocking skill sessions). |

---

## **Next Steps**
1. **Approve Plan**: User confirms the implementation scope.
2. **Task 1**: Implement `skill-creator.md` to enable the "Design" phase.
3. **Task 2**: Develop the `SkillBenchmarkTool` to enable the "Eval" phase.
