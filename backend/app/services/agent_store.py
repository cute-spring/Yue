import json
import os
import shutil
import threading
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

def _default_data_dir() -> str:
    return os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))


def _timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")

class AgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    system_prompt: str
    provider: str = "openai"
    model: str = "gpt-4o"
    enabled_tools: List[str] = [] # List of tool names
    doc_roots: List[str] = []
    doc_file_patterns: List[str] = []
    require_citations: bool = False
    skill_mode: str = "off"  # off | manual | auto
    visible_skills: List[str] = []
    agent_kind: str = "traditional"
    skill_groups: List[str] = []
    extra_visible_skills: List[str] = []
    resolved_visible_skills: List[str] = []
    voice_input_enabled: bool = True
    voice_input_provider: str = "browser"  # browser | azure
    voice_azure_config: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class AgentStore:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or _default_data_dir()
        self.agents_file = os.path.join(self.data_dir, "agents.json")
        self.agents_backup_file = f"{self.agents_file}.bak"
        self._lock = threading.RLock()
        self._ensure_data_file()
        self._ensure_builtin_agents()

    def _ensure_data_file(self):
        os.makedirs(self.data_dir, exist_ok=True)

        if os.path.exists(self.agents_file):
            return

        self._atomic_write_json(
            self.agents_file,
            [agent.model_dump(mode="json") for agent in self._builtin_agents()],
        )

    def _atomic_write_json(self, path: str, data) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp.{_timestamp_tag()}"
        try:
            if os.path.exists(path):
                try:
                    shutil.copy2(path, f"{path}.bak")
                except Exception:
                    pass
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def _recover_agents_file_if_needed(self) -> bool:
        if not os.path.exists(self.agents_file):
            return False
        try:
            with open(self.agents_file, "r") as f:
                json.load(f)
            return True
        except Exception:
            pass

        if os.path.exists(self.agents_backup_file):
            try:
                with open(self.agents_backup_file, "r") as f:
                    data = json.load(f)
                self._atomic_write_json(self.agents_file, data)
                return True
            except Exception:
                pass

        corrupt = f"{self.agents_file}.corrupt.{_timestamp_tag()}"
        try:
            os.replace(self.agents_file, corrupt)
        except Exception:
            pass

        self._atomic_write_json(
            self.agents_file,
            [agent.model_dump(mode="json") for agent in self._builtin_agents()],
        )
        return True

    def _builtin_agents(self) -> List[AgentConfig]:
        return [
            self._builtin_docs_agent(),
            self._builtin_local_docs_agent(),
            self._builtin_architect_agent(),
            self._builtin_excel_analyst_agent(),
            self._builtin_pdf_research_agent(),
            self._builtin_ppt_builder_agent(),
            self._builtin_action_lab_agent(),
            self._builtin_translator_agent(),
        ]

    def _builtin_docs_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-docs",
            name="Document Assistant",
            system_prompt=(
                "Role: You are a helpful assistant specialized in using MCP tools to find and retrieve relevant documents, including PDFs, from the Yue/docs repository.\n"
                "Scope/Boundaries: Your capabilities are restricted to searching and reading documents within the Yue/docs directory. You can execute shell commands only for document retrieval purposes and must avoid any harmful or unauthorized actions.\n"
                "Workflow: When a user queries, first use keyword search tools (docs_search and docs_search_pdf) to identify relevant files. If search results are insufficient, use docs_read or docs_read_pdf to retrieve full content. Use docs_list to explore directory structures if needed. Optionally, use exec for advanced retrieval tasks, but with caution.\n"
                "Output Format: Provide clear and concise answers, citing specific documents or snippets with file paths and line numbers where applicable.\n"
                "Prohibitions: Do not access files outside Yue/docs. Do not execute commands that could harm the system or violate security. Do not generate or modify files unless explicitly instructed.\n\n"
                "## 文件路径处理规范\n"
                "- 若用户仅提供文件名（如 `ar_2024_en.pdf`），优先在 `docs/` 目录下查找，并使用完整路径格式：`docs/文件名`。\n"
                "- 若用户未明确提供路径（例如“root folder 下有什么文件”），第一步必须调用 `docs_list` 且不传 `root_dir`；这里的 root folder 指有效 docs 根目录。\n"
                "- 仅在用户明确指定目录时才传 `root_dir`；若 `root_dir` 报错，立即省略 `root_dir` 重试一次。\n"
                "- 在回答中若引用文档，必须注明完整路径（如 `docs/ar_2024_en.pdf#P1-P4`），方便用户复核。"
            ),
            provider="deepseek",
            model="deepseek-reasoner",
            enabled_tools=[
                "builtin:docs_search",
                "builtin:docs_search_pdf",
                "builtin:docs_read",
                "builtin:docs_read_pdf",
                "builtin:docs_list",
                "builtin:exec",
                "builtin:pdf_keyword_page_search",
                "builtin:pdf_page_render_image",
                "builtin:pdf_page_text_read"
            ],
            doc_file_patterns=["**/*.md", "**/*.yaml", "**/*.yml", "**/*.pdf"],
            require_citations=True,
            skill_mode="auto",
            visible_skills=["pdf-insight-extractor:1.0.0"],
        )

    def _builtin_local_docs_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-local-docs",
            name="Local Docs",
            system_prompt=(
                "你是一个专门基于用户提供的本地目录中的文档（如 Markdown、文本、日志等）回答问题的助手。\n"
                "你必须首先使用 docs_search / docs_read 工具在指定目录下检索证据，然后再给出回答。\n"
                "用户可以提供一个或多个目录；如果提供多个目录，请按目录逐个检索并合并命中结果。\n"
                "你的工作流程：\n"
                "1. 确认用户提供的目录路径。\n"
                "2. 使用 docs_search(root_dir=目录) 在目录下搜索关键词（模式默认为 text 以支持多种格式）。\n"
                "3. 使用 docs_read(root_dir=目录) 读取相关文档的详细内容。\n"
                "4. 基于找到的内容回答问题，并在回答中附带引用的文件路径（path）。\n"
                "如果找不到证据：明确说明“在指定目录下未找到相关文档依据”，不要用常识或猜测补全，并给出可继续检索的建议。\n"
                "安全提示：你只能访问被系统允许的白名单目录。如果目录不合法，工具会返回错误，请如实告知用户。"
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:docs_list",
                "builtin:docs_search",
                "builtin:docs_read",
            ],
            doc_file_patterns=["**/*.md", "**/*.txt", "**/*.log", "**/*.json", "**/*.yaml", "**/*.yml"],
            require_citations=True,
            skill_mode="manual",
            visible_skills=["project-status-auditor:1.0.0"],
        )

    def _builtin_architect_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-architect",
            name="System Architect",
            system_prompt=(
                "You are an expert system architect who excels at visual communication through UML diagrams. "
                "Your core principle: \"A picture is worth a thousand words\" - always visualize complex concepts.\n\n"
                "VISUALIZATION GUIDELINES:\n"
                "1. Proactive Visualization: When users ask about system architecture, workflows, or data flows, generate diagrams.\n"
                "2. Mermaid Syntax: Always use ```mermaid code blocks with proper language identifier.\n"
                "3. Best Practices: Use Sequence Diagrams for interactions, Flowcharts for logic, and ER Diagrams for data models.\n"
                "4. Structure: Visualize first, explain second. Users love diagrams!"
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[],
        )

    def _builtin_excel_analyst_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-excel-analyst",
            name="Excel Analyst",
            system_prompt=(
                "Role: Senior Excel Data Analyst & Automation Expert\n"
                "You are a professional analyst specializing in Excel-driven business intelligence and data forensics. "
                "Deliver accurate, high-performance, and secure analysis using built-in Excel tools.\n\n"
                "Tool Strategy (Phase-Based Execution):\n"
                "1. Structural awareness first: always run excel_profile before reading or querying.\n"
                "2. Security and logic checks when needed: use excel_script_scan for untrusted files and excel_logic_extract for formula lineage.\n"
                "3. Retrieval by scale: excel_read for small datasets, excel_query for large/complex analysis.\n\n"
                "Analytical principles:\n"
                "- Prefer excel_query for search, aggregation, grouping, and joins.\n"
                "- Query only virtual table excel_data with SELECT statements.\n"
                "- Cite exact sheet and range in final responses.\n"
                "- If output is truncated, tell the user and narrow the query scope.\n\n"
                "Constraints:\n"
                "- Treat source files as read-only.\n"
                "- Respect hidden rows/columns unless task-relevant."
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:excel_profile",
                "builtin:excel_read",
                "builtin:excel_query",
                "builtin:excel_logic_extract",
                "builtin:excel_script_scan",
            ],
            doc_file_patterns=["**/*.xlsx", "**/*.xlsm", "**/*.csv"],
            require_citations=True,
            skill_mode="manual",
            visible_skills=["excel-metric-explorer:1.0.0"],
        )

    def _builtin_pdf_research_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-pdf-research",
            name="PDF Researcher",
            system_prompt=(
                "Role: You are a PDF evidence researcher specialized in extracting high-signal findings from reports, filings, and technical PDFs.\n"
                "Workflow: Use PDF search/navigation tools first to locate relevant pages, then read the exact pages and cite the page ranges you relied on.\n"
                "Skill behavior: Prefer the pdf-insight-extractor skill when the user asks for keyword-driven extraction, evidence gathering, or page-level summarization.\n"
                "Output format: Return a concise answer with bulletable findings, exact page references, and any follow-up keyword suggestions if evidence is thin.\n"
                "Prohibitions: Do not guess missing evidence, and do not cite pages you did not inspect."
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:pdf_keyword_page_search",
                "builtin:pdf_page_text_read",
                "builtin:pdf_page_table_extract",
                "builtin:pdf_outline_extract",
                "builtin:pdf_page_range_filter",
            ],
            doc_file_patterns=["**/*.pdf"],
            require_citations=True,
            skill_mode="manual",
            visible_skills=["pdf-insight-extractor:1.0.0"],
        )

    def _builtin_ppt_builder_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-ppt-builder",
            name="PPT Builder",
            system_prompt=(
                "Role: You are a deck-building assistant for fast validation of Yue's artifact-generation flow.\n"
                "Workflow: Draft a tight outline, confirm it when needed, then use generate_pptx to produce the file. After generation, surface the filename and download path clearly.\n"
                "Skill behavior: Prefer the ppt-expert skill for slide planning and artifact generation.\n"
                "Output format: Keep answers brief, include the generated artifact summary, and return the Markdown download link after success.\n"
                "Prohibitions: Do not fabricate download paths or claim a PPT was generated unless the tool returned success."
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=["builtin:generate_pptx"],
            skill_mode="manual",
            visible_skills=["ppt-expert:1.0.0"],
        )

    def _builtin_action_lab_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-action-lab",
            name="Action Lab",
            system_prompt=(
                "Role: You are a verification-focused operator for Yue's tool-backed skill actions.\n"
                "Workflow: When the user wants to test action flows, explicitly help them exercise validation, approval, execution, and trace inspection. Use the narrowest appropriate skill and tool path.\n"
                "Skill behavior: Prefer system-ops-expert for exec-backed flows, code-simplifier for cleanup workflows, and ppt-expert for artifact-generation checks.\n"
                "Testing mindset: Call out which phase is being exercised: preflight, approval, execution, or trace review. If inputs are intentionally invalid, explain the expected blocked outcome before acting.\n"
                "Prohibitions: Do not use unrelated tools, and do not hide raw tool/action results that are needed for debugging."
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:exec",
                "builtin:docs_search",
                "builtin:docs_read",
                "builtin:generate_pptx",
            ],
            doc_file_patterns=["**/*.md", "**/*.txt", "**/*.yaml", "**/*.yml", "**/*.json"],
            skill_mode="manual",
            visible_skills=[
                "system-ops-expert:1.0.0",
                "code-simplifier:1.0.0",
                "ppt-expert:1.0.0",
            ],
            require_citations=False,
        )

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

    def _ensure_builtin_agents(self):
        agents = self.list_agents()
        builtins = self._builtin_agents()
        
        changed_any = False
        for builtin in builtins:
            found = False
            for i, a in enumerate(agents):
                if a.id == builtin.id:
                    found = True
                    changed = False
                    if a.system_prompt != builtin.system_prompt:
                        a.system_prompt = builtin.system_prompt
                        changed = True
                    if a.enabled_tools != builtin.enabled_tools:
                        a.enabled_tools = builtin.enabled_tools
                        changed = True
                    if a.doc_roots != builtin.doc_roots:
                        a.doc_roots = builtin.doc_roots
                        changed = True
                    if getattr(a, "doc_file_patterns", None) != builtin.doc_file_patterns:
                        a.doc_file_patterns = builtin.doc_file_patterns
                        changed = True
                    if getattr(a, "require_citations", None) != builtin.require_citations:
                        a.require_citations = builtin.require_citations
                        changed = True
                    if getattr(a, "skill_mode", None) != builtin.skill_mode:
                        a.skill_mode = builtin.skill_mode
                        changed = True
                    if getattr(a, "visible_skills", None) != builtin.visible_skills:
                        a.visible_skills = builtin.visible_skills
                        changed = True
                    if changed:
                        agents[i] = a
                        changed_any = True
                    break
            
            if not found:
                agents.append(builtin)
                changed_any = True
        
        if changed_any:
            self._save_agents(agents)

    def list_agents(self) -> List[AgentConfig]:
        with self._lock:
            self._ensure_data_file()
            self._recover_agents_file_if_needed()
            try:
                with open(self.agents_file, "r") as f:
                    data = json.load(f)
            except Exception:
                data = []
            if not isinstance(data, list):
                data = []
            return [AgentConfig(**item) for item in data]

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        with self._lock:
            agents = self.list_agents()
            for agent in agents:
                if agent.id == agent_id:
                    return agent
            return None

    def create_agent(self, agent: AgentConfig) -> AgentConfig:
        with self._lock:
            agents = self.list_agents()
            agents.append(agent)
            self._save_agents(agents)
            return agent

    def update_agent(self, agent_id: str, updates: dict) -> Optional[AgentConfig]:
        with self._lock:
            agents = self.list_agents()
            for i, agent in enumerate(agents):
                if agent.id == agent_id:
                    updated_data = agent.model_dump()
                    for k, v in updates.items():
                        updated_data[k] = v

                    updated_data["updated_at"] = datetime.now()
                    new_agent = AgentConfig(**updated_data)
                    agents[i] = new_agent
                    self._save_agents(agents)
                    return new_agent
            return None

    def delete_agent(self, agent_id: str) -> bool:
        with self._lock:
            agents = self.list_agents()
            initial_len = len(agents)
            agents = [a for a in agents if a.id != agent_id]
            if len(agents) < initial_len:
                self._save_agents(agents)
                return True
            return False

    def _save_agents(self, agents: List[AgentConfig]):
        self._atomic_write_json(self.agents_file, [a.model_dump(mode="json") for a in agents])

agent_store = AgentStore()
