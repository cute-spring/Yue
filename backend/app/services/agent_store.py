import json
import os
import shutil
import threading
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

def _default_data_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))


def _legacy_data_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))


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
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class AgentStore:
    def __init__(self, data_dir: Optional[str] = None, legacy_data_dir: Optional[str] = None):
        self.data_dir = data_dir or _default_data_dir()
        self.legacy_data_dir = legacy_data_dir or _legacy_data_dir()
        self.agents_file = os.path.join(self.data_dir, "agents.json")
        self.agents_backup_file = f"{self.agents_file}.bak"
        self._lock = threading.RLock()
        self._ensure_data_file()
        self._ensure_builtin_agents()

    def _ensure_data_file(self):
        os.makedirs(self.data_dir, exist_ok=True)

        if os.path.exists(self.agents_file):
            return

        legacy_agents_file = os.path.join(self.legacy_data_dir, "agents.json")
        if os.path.exists(legacy_agents_file):
            try:
                with open(legacy_agents_file, "r") as f:
                    data = json.load(f)
                self._atomic_write_json(self.agents_file, data)
                return
            except Exception:
                corrupt = f"{legacy_agents_file}.corrupt.{_timestamp_tag()}"
                try:
                    os.replace(legacy_agents_file, corrupt)
                except Exception:
                    pass

        self._atomic_write_json(
            self.agents_file,
            [
                self._builtin_docs_agent().model_dump(mode="json"),
                self._builtin_local_docs_agent().model_dump(mode="json"),
            ],
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
            [
                self._builtin_docs_agent().model_dump(mode="json"),
                self._builtin_local_docs_agent().model_dump(mode="json"),
            ],
        )
        return True

    def _builtin_docs_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-docs",
            name="Docs",
            system_prompt=(
                "你是一个只基于 Yue/docs 下 Markdown 文档回答问题的助手。\n"
                "你必须先使用 docs_search / docs_read 工具检索证据，再给出回答。\n"
                "检索 Markdown 时：优先使用 docs_search(mode=\"markdown\") 或设置 doc_file_patterns 只允许 *.md。\n"
                "如果找不到证据：明确说明“未在文档中找到依据”，不要用常识或猜测补全，并给出可继续检索的关键词建议。\n"
                "输出要求：列出答案要点，并附带引用路径（来自工具返回的 path）。"
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:docs_search",
                "builtin:docs_read",
            ],
            doc_file_patterns=["**/*.md"],
            require_citations=True,
        )

    def _builtin_local_docs_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-local-docs",
            name="Local Docs",
            system_prompt=(
                "你是一个专门基于用户提供的本地目录中的 Markdown 文档回答问题的助手。\n"
                "你必须首先使用 docs_search / docs_read 工具在指定目录下检索证据，然后再给出回答。\n"
                "用户可以提供一个或多个目录；如果提供多个目录，请按目录逐个检索并合并命中结果。\n"
                "你的工作流程：\n"
                "1. 确认用户提供的目录路径。\n"
                "2. 使用 docs_search(root_dir=目录, mode=\"markdown\") 在目录下搜索关键词。\n"
                "3. 使用 docs_read(root_dir=目录, mode=\"markdown\") 读取相关文档的详细内容。\n"
                "4. 基于找到的内容回答问题，并在回答中附带引用的文件路径（path）。\n"
                "如果找不到证据：明确说明“在指定目录下未找到相关文档依据”，不要用常识或猜测补全，并给出可继续检索的建议。\n"
                "安全提示：你只能访问被系统允许的白名单目录。如果目录不合法，工具会返回错误，请如实告知用户。"
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:docs_search",
                "builtin:docs_read",
            ],
            doc_file_patterns=["**/*.md"],
            require_citations=True,
        )

    def _ensure_builtin_agents(self):
        agents = self.list_agents()
        builtins = [self._builtin_docs_agent(), self._builtin_local_docs_agent()]
        
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
