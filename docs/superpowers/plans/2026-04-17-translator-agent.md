# Built-in Translator Agent Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a built-in bilingual translator agent to Yue that provides professional translation between Chinese and English while preserving terminology and formatting.

**Architecture:** Extend the `AgentStore` in the backend to include a new built-in agent definition and register it in the initialization flow.

**Tech Stack:** Python, Pydantic, FastAPI (backend).

---

## Chunk 1: Backend Implementation

### Task 1: Add `_builtin_translator_agent` to `AgentStore`

**Files:**
- Modify: `backend/app/services/agent_store.py`

- [ ] **Step 1: Implement the `_builtin_translator_agent` method**

Add the following method to the `AgentStore` class in `backend/app/services/agent_store.py`:

```python
    def _builtin_translator_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-translator",
            name="双语翻译专家 (Bilingual Translator)",
            system_prompt=(
                "你是一个专业的中英文双语翻译专家，擅长在保持技术严谨性的同时，提供优雅且符合语境的翻译。\n\n"
                "核心职责：\n"
                "1. **双向翻译**：自动检测输入语言。如果是英文则翻译成中文；如果是中文则翻译成英文。\n"
                "2. **术语保留策略**：对于专业技术词汇（如 RAG, LLM, Kubernetes 等），请遵循以下格式：\n"
                "   - 英文转中文：使用 `翻译内容 (英文原词)`，例如：`检索增强生成 (RAG)`。\n"
                "   - 中文转英文：直接翻译为对应的专业术语。\n"
                "3. **格式保持**：严格保持原始输入中的所有 Markdown 格式，包括但不限于：\n"
                "   - 代码块 (Code blocks)\n"
                "   - 链接 (Links)\n"
                "   - 加粗/斜体 (Bold/Italic)\n"
                "   - 列表 (Lists)\n"
                "   - 数学公式 (LaTeX)\n"
                "4. **信达雅**：翻译应准确（信）、通顺（达）、优雅（雅），避免生硬的字面翻译。\n"
                "5. **语气**：保持专业、中立、客观的语气。"
            ),
            provider="deepseek",
            model="deepseek-reasoner",
            enabled_tools=[],
            skill_mode="off",
        )
```

- [ ] **Step 2: Register the agent in `_builtin_agents`**

Update the `_builtin_agents` method to include the new translator agent:

```python
    def _builtin_agents(self) -> List[AgentConfig]:
        return [
            self._builtin_docs_agent(),
            self._builtin_local_docs_agent(),
            self._builtin_architect_agent(),
            self._builtin_excel_analyst_agent(),
            self._builtin_pdf_research_agent(),
            self._builtin_ppt_builder_agent(),
            self._builtin_action_lab_agent(),
            self._builtin_translator_agent(), # Add this line
        ]
```

- [ ] **Step 3: Commit changes**

```bash
git add backend/app/services/agent_store.py
git commit -m "feat: add built-in translator agent"
```

## Chunk 2: Verification

### Task 2: Verify Agent Registration

**Files:**
- Test: `backend/tests/test_agent_store_unit.py`

- [ ] **Step 1: Update unit test to check for the new agent**

Modify `backend/tests/test_agent_store_unit.py` to assert the existence of the translator agent.

```python
def test_list_agents(agent_store):
    agents = agent_store.list_agents()
    assert len(agents) >= 8 # Incremented from 7
    assert agents[0].id == "builtin-docs"
    assert any(a.id == "builtin-excel-analyst" for a in agents)
    assert any(a.id == "builtin-pdf-research" for a in agents)
    assert any(a.id == "builtin-ppt-builder" for a in agents)
    assert any(a.id == "builtin-action-lab" for a in agents)
    assert any(a.id == "builtin-translator" for a in agents) # Add this assertion
```

- [ ] **Step 2: Run unit tests**

Run: `pytest backend/tests/test_agent_store_unit.py`
Expected: PASS

- [ ] **Step 3: Commit changes**

```bash
git add backend/tests/test_agent_store_unit.py
git commit -m "test: verify translator agent registration"
```
