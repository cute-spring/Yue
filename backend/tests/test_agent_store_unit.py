import pytest
import os
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from app.services.agent_store import AgentStore, AgentConfig

@pytest.fixture
def temp_dirs():
    data_dir = tempfile.mkdtemp()
    legacy_dir = tempfile.mkdtemp()
    yield data_dir, legacy_dir
    shutil.rmtree(data_dir)
    shutil.rmtree(legacy_dir)

@pytest.fixture
def agent_store(temp_dirs):
    data_dir, _legacy_dir = temp_dirs
    return AgentStore(data_dir=data_dir)

def test_ensure_data_file_creates_file(temp_dirs):
    data_dir, _legacy_dir = temp_dirs
    store = AgentStore(data_dir=data_dir)
    assert os.path.exists(os.path.join(data_dir, "agents.json"))

def test_no_legacy_path_uses_runtime_data_only(temp_dirs):
    data_dir, legacy_dir = temp_dirs
    legacy_file = os.path.join(legacy_dir, "agents.json")
    with open(legacy_file, "w") as f:
        json.dump([{"id": "legacy-1", "name": "Legacy Agent", "system_prompt": "legacy"}], f)

    store = AgentStore(data_dir=data_dir)
    agents = store.list_agents()
    assert all(a.id != "legacy-1" for a in agents)
    assert any(a.id == "builtin-docs" for a in agents)

def test_list_agents(agent_store):
    agents = agent_store.list_agents()
    assert len(agents) >= 4
    assert agents[0].id == "builtin-docs"
    assert any(a.id == "builtin-excel-analyst" for a in agents)

def test_create_agent(agent_store):
    new_agent = AgentConfig(name="New Agent", system_prompt="You are a helper")
    created = agent_store.create_agent(new_agent)
    assert created.id == new_agent.id
    
    agents = agent_store.list_agents()
    assert any(a.id == new_agent.id for a in agents)

def test_get_agent(agent_store):
    agent = agent_store.get_agent("builtin-docs")
    assert agent is not None
    assert agent.id == "builtin-docs"
    
    assert agent_store.get_agent("non-existent") is None

def test_update_agent(agent_store):
    updated = agent_store.update_agent("builtin-docs", {"name": "Updated Docs"})
    assert updated is not None
    assert updated.name == "Updated Docs"
    
    agent = agent_store.get_agent("builtin-docs")
    assert agent.name == "Updated Docs"

def test_update_agent_not_found(agent_store):
    assert agent_store.update_agent("non-existent", {"name": "fail"}) is None

def test_delete_agent(agent_store):
    new_agent = AgentConfig(name="To Delete", system_prompt="bye")
    agent_store.create_agent(new_agent)
    
    assert agent_store.delete_agent(new_agent.id) is True
    assert agent_store.get_agent(new_agent.id) is None

def test_delete_agent_not_found(agent_store):
    assert agent_store.delete_agent("non-existent") is False

def test_atomic_write_backup(temp_dirs):
    data_dir, _legacy_dir = temp_dirs
    store = AgentStore(data_dir=data_dir)
    path = os.path.join(data_dir, "test.json")
    
    store._atomic_write_json(path, {"a": 1})
    assert os.path.exists(path)
    
    store._atomic_write_json(path, {"a": 2})
    assert os.path.exists(path + ".bak")
    with open(path, "r") as f:
        assert json.load(f)["a"] == 2

def test_recover_corrupt_file(temp_dirs):
    data_dir, _legacy_dir = temp_dirs
    agents_file = os.path.join(data_dir, "agents.json")
    os.makedirs(data_dir, exist_ok=True)
    with open(agents_file, "w") as f:
        f.write("invalid json")
    
    store = AgentStore(data_dir=data_dir)
    # list_agents should trigger recovery
    agents = store.list_agents()
    assert len(agents) >= 4
    assert any(a.id == "builtin-docs" for a in agents)
    assert any(a.id == "builtin-excel-analyst" for a in agents)
    # Should have created a corrupt file
    files = os.listdir(data_dir)
    assert any(f.startswith("agents.json.corrupt") for f in files)


def test_builtin_docs_prompt_root_dir_rules(agent_store):
    agent = agent_store.get_agent("builtin-docs")
    assert agent is not None
    prompt = agent.system_prompt
    assert "root folder 指有效 docs 根目录" in prompt
    assert "第一步必须调用 `docs_list` 且不传 `root_dir`" in prompt
    assert "仅在用户明确指定目录时才传 `root_dir`" in prompt
    assert "必须显式指定 `root_dir`" not in prompt

def test_migrate_agents_script_dry_run(temp_dirs):
    data_dir, legacy_dir = temp_dirs
    legacy_file = os.path.join(legacy_dir, "agents.json")
    runtime_file = os.path.join(data_dir, "agents.json")
    with open(legacy_file, "w") as f:
        json.dump([{"id": "legacy-1", "name": "Legacy Agent", "system_prompt": "legacy"}], f)

    backend_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            "python",
            "scripts/migrate_agents_to_runtime_data.py",
            "--legacy-file",
            legacy_file,
            "--runtime-file",
            runtime_file,
            "--dry-run",
        ],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "dry_run" in result.stdout
    assert not os.path.exists(runtime_file)


def test_agent_config_defaults_include_agent_kind():
    cfg = AgentConfig(name="x", system_prompt="y")
    assert cfg.agent_kind == "traditional"
    assert cfg.skill_groups == []
    assert cfg.extra_visible_skills == []
    assert cfg.voice_input_enabled is True
    assert cfg.voice_input_provider == "browser"
    assert cfg.voice_azure_config is None


def test_agent_store_loads_legacy_record_with_new_defaults(temp_dirs):
    data_dir, _legacy_dir = temp_dirs
    store = AgentStore(data_dir=data_dir)
    agents_file = os.path.join(data_dir, "agents.json")
    with open(agents_file, "w") as f:
        json.dump(
            [
                {
                    "id": "legacy-agent",
                    "name": "Legacy Agent",
                    "system_prompt": "legacy",
                    "provider": "openai",
                    "model": "gpt-4o",
                    "enabled_tools": [],
                    "skill_mode": "manual",
                    "visible_skills": ["planner:1.0.0"],
                }
            ],
            f,
        )

    loaded = store.get_agent("legacy-agent")
    assert loaded is not None
    assert loaded.agent_kind == "traditional"
    assert loaded.skill_groups == []
    assert loaded.extra_visible_skills == []
    assert loaded.voice_input_enabled is True
    assert loaded.voice_input_provider == "browser"
    assert loaded.voice_azure_config is None
