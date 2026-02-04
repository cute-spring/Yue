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
    doc_root: str = "docs"
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
                json.dump([self._builtin_docs_agent().model_dump(mode="json")], f, indent=2)

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
            doc_root="docs",
        )

    def _ensure_builtin_agents(self):
        agents = self.list_agents()
        builtin = self._builtin_docs_agent()
        for i, a in enumerate(agents):
            if a.id != "builtin-docs":
                continue
            changed = False
            if a.system_prompt != builtin.system_prompt:
                a.system_prompt = builtin.system_prompt
                changed = True
            if a.enabled_tools != builtin.enabled_tools:
                a.enabled_tools = builtin.enabled_tools
                changed = True
            if changed:
                agents[i] = a
                self._save_agents(agents)
            return
        agents.append(builtin)
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
