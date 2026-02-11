import pytest
import os
import json
import shutil
import tempfile
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
    data_dir, legacy_dir = temp_dirs
    return AgentStore(data_dir=data_dir, legacy_data_dir=legacy_dir)

def test_ensure_data_file_creates_file(temp_dirs):
    data_dir, legacy_dir = temp_dirs
    store = AgentStore(data_dir=data_dir, legacy_data_dir=legacy_dir)
    assert os.path.exists(os.path.join(data_dir, "agents.json"))

def test_ensure_data_file_from_legacy(temp_dirs):
    data_dir, legacy_dir = temp_dirs
    legacy_file = os.path.join(legacy_dir, "agents.json")
    legacy_data = [{"id": "legacy-1", "name": "Legacy Agent", "system_prompt": "test", "provider": "openai", "model": "gpt-4o"}]
    with open(legacy_file, "w") as f:
        json.dump(legacy_data, f)
    
    store = AgentStore(data_dir=data_dir, legacy_data_dir=legacy_dir)
    agents = store.list_agents()
    # Should contain legacy agent + 2 builtin agents
    assert any(a.id == "legacy-1" for a in agents)
    assert any(a.id == "builtin-docs" for a in agents)

def test_list_agents(agent_store):
    agents = agent_store.list_agents()
    assert len(agents) >= 2
    assert agents[0].id == "builtin-docs"

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
    data_dir, legacy_dir = temp_dirs
    store = AgentStore(data_dir=data_dir, legacy_data_dir=legacy_dir)
    path = os.path.join(data_dir, "test.json")
    
    store._atomic_write_json(path, {"a": 1})
    assert os.path.exists(path)
    
    store._atomic_write_json(path, {"a": 2})
    assert os.path.exists(path + ".bak")
    with open(path, "r") as f:
        assert json.load(f)["a"] == 2

def test_recover_corrupt_file(temp_dirs):
    data_dir, legacy_dir = temp_dirs
    agents_file = os.path.join(data_dir, "agents.json")
    os.makedirs(data_dir, exist_ok=True)
    with open(agents_file, "w") as f:
        f.write("invalid json")
    
    store = AgentStore(data_dir=data_dir, legacy_data_dir=legacy_dir)
    # list_agents should trigger recovery
    agents = store.list_agents()
    assert len(agents) >= 2
    assert any(a.id == "builtin-docs" for a in agents)
    # Should have created a corrupt file
    files = os.listdir(data_dir)
    assert any(f.startswith("agents.json.corrupt") for f in files)
