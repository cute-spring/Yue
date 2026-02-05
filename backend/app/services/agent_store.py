import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
AGENTS_FILE = os.path.join(DATA_DIR, "agents.json")

class AgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    system_prompt: str
    provider: str = "openai"
    model: str = "gpt-4o"
    enabled_tools: List[str] = [] # List of tool names
    doc_roots: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class AgentStore:
    def __init__(self):
        self._ensure_data_file()
        self._ensure_builtin_agents()

    def _ensure_data_file(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(AGENTS_FILE):
            with open(AGENTS_FILE, 'w') as f:
                json.dump([
                    self._builtin_docs_agent().model_dump(mode="json"),
                    self._builtin_local_docs_agent().model_dump(mode="json")
                ], f, indent=2)

    def _builtin_docs_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-docs",
            name="Docs",
            system_prompt=(
                "你是一个只基于 Yue/docs 下 Markdown 文档回答问题的助手。\n"
                "你必须先使用 docs_search_markdown / docs_read_markdown 工具检索证据，再给出回答。\n"
                "如果找不到证据：明确说明“未在文档中找到依据”，不要用常识或猜测补全，并给出可继续检索的关键词建议。\n"
                "输出要求：列出答案要点，并附带引用路径（来自工具返回的 path）。"
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:docs_search_markdown",
                "builtin:docs_read_markdown",
            ],
        )

    def _builtin_local_docs_agent(self) -> AgentConfig:
        return AgentConfig(
            id="builtin-local-docs",
            name="Local Docs",
            system_prompt=(
                "你是一个专门基于用户提供的本地目录中的 Markdown 文档回答问题的助手。\n"
                "你必须首先使用 docs_search_markdown_dir / docs_read_markdown_dir 工具在指定目录下检索证据，然后再给出回答。\n"
                "用户可以提供一个或多个目录；如果提供多个目录，请按目录逐个检索并合并命中结果。\n"
                "你的工作流程：\n"
                "1. 确认用户提供的目录路径。\n"
                "2. 使用 docs_search_markdown_dir 在目录下搜索关键词。\n"
                "3. 使用 docs_read_markdown_dir 读取相关文档的详细内容。\n"
                "4. 基于找到的内容回答问题，并在回答中附带引用的文件路径（path）。\n"
                "如果找不到证据：明确说明“在指定目录下未找到相关文档依据”，不要用常识或猜测补全，并给出可继续检索的建议。\n"
                "安全提示：你只能访问被系统允许的白名单目录。如果目录不合法，工具会返回错误，请如实告知用户。"
            ),
            provider="openai",
            model="gpt-4o",
            enabled_tools=[
                "builtin:docs_search_markdown_dir",
                "builtin:docs_read_markdown_dir",
            ],
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
        with open(AGENTS_FILE, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return []
            return [AgentConfig(**item) for item in data]

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        agents = self.list_agents()
        for agent in agents:
            if agent.id == agent_id:
                return agent
        return None

    def create_agent(self, agent: AgentConfig) -> AgentConfig:
        agents = self.list_agents()
        agents.append(agent)
        self._save_agents(agents)
        return agent

    def update_agent(self, agent_id: str, updates: dict) -> Optional[AgentConfig]:
        agents = self.list_agents()
        for i, agent in enumerate(agents):
            if agent.id == agent_id:
                updated_data = agent.model_dump()
                # Remove fields that shouldn't be updated via dict merge if necessary
                # But for now simple update
                for k, v in updates.items():
                    updated_data[k] = v
                
                updated_data['updated_at'] = datetime.now()
                # Re-validate
                new_agent = AgentConfig(**updated_data)
                agents[i] = new_agent
                self._save_agents(agents)
                return new_agent
        return None

    def delete_agent(self, agent_id: str) -> bool:
        agents = self.list_agents()
        initial_len = len(agents)
        agents = [a for a in agents if a.id != agent_id]
        if len(agents) < initial_len:
            self._save_agents(agents)
            return True
        return False

    def _save_agents(self, agents: List[AgentConfig]):
        with open(AGENTS_FILE, 'w') as f:
            json.dump([json.loads(a.model_dump_json()) for a in agents], f, indent=2)

agent_store = AgentStore()
