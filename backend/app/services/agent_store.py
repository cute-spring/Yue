import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.builtin_agent_catalog import BuiltinAgentCatalog


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
    model_selection_mode: str = "direct"  # direct | tier
    model_tier: str = "balanced"  # light | balanced | heavy
    model_role: Optional[str] = None
    model_policy: str = "prefer_role"  # prefer_role | force_direct | system_default
    upgrade_on_tools: bool = True
    upgrade_on_multi_skill: bool = True
    enabled_tools: List[str] = []
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
    voice_input_provider: str = "browser"
    voice_azure_config: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AgentStore:
    def __init__(
        self,
        data_dir: Optional[str] = None,
        builtin_agents_dir: Optional[str] = None,
    ):
        self.data_dir = data_dir or _default_data_dir()
        self.agents_file = os.path.join(self.data_dir, "agents.json")
        self.agents_backup_file = f"{self.agents_file}.bak"
        self._builtin_catalog = BuiltinAgentCatalog(builtin_agents_dir=builtin_agents_dir)
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
        agents: List[AgentConfig] = []
        for spec in self._builtin_catalog.list_builtin_agents():
            agents.append(AgentConfig(**spec.payload))
        return agents

    def _ensure_builtin_agents(self):
        agents = self.list_agents()
        builtins = self._builtin_agents()

        changed_any = False
        existing_ids = {agent.id for agent in agents}
        for builtin in builtins:
            if builtin.id in existing_ids:
                continue
            agents.append(builtin)
            existing_ids.add(builtin.id)
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
