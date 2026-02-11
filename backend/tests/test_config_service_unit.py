import os
import json
import pytest
from pathlib import Path
from app.services.config_service import ConfigService

@pytest.fixture
def temp_config_file(tmp_path):
    config_dir = tmp_path / "data"
    config_dir.mkdir()
    config_file = config_dir / "global_config.json"
    return config_file

def test_config_service_init_creates_dir(tmp_path):
    config_path = tmp_path / "new_dir" / "config.json"
    service = ConfigService(str(config_path))
    assert config_path.parent.exists()
    assert service.get_config() == {}

def test_config_service_load_existing(temp_config_file):
    data = {"llm": {"provider": "openai"}}
    temp_config_file.write_text(json.dumps(data))
    service = ConfigService(str(temp_config_file))
    assert service.get_config() == data

def test_config_service_update(temp_config_file):
    service = ConfigService(str(temp_config_file))
    new_data = {"preferences": {"theme": "dark"}}
    service.update_config(new_data)
    
    # Check memory
    assert service.get_config() == new_data
    # Check disk
    with open(temp_config_file, 'r') as f:
        assert json.load(f) == new_data

def test_get_llm_config_merges_env(temp_config_file, monkeypatch):
    data = {"llm": {"openai_model": "gpt-4"}}
    temp_config_file.write_text(json.dumps(data))
    
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "30")
    
    service = ConfigService(str(temp_config_file))
    llm_config = service.get_llm_config()
    
    assert llm_config["openai_model"] == "gpt-4"
    assert llm_config["openai_api_key"] == "sk-test-key"
    assert llm_config["llm_request_timeout"] == 30

def test_update_llm_config_protects_secrets(temp_config_file):
    data = {"llm": {"openai_api_key": "secret-key", "provider": "openai"}}
    temp_config_file.write_text(json.dumps(data))
    service = ConfigService(str(temp_config_file))
    
    # Try to overwrite with masked value
    service.update_llm_config({"openai_api_key": "****", "provider": "ollama"})
    
    llm_config = service.get_llm_config()
    assert llm_config["openai_api_key"] == "secret-key"
    assert llm_config["provider"] == "ollama"

def test_custom_models_crud(temp_config_file):
    service = ConfigService(str(temp_config_file))
    
    # Create
    model = {"name": "test-model", "api_key": "key1"}
    service.upsert_custom_model(model)
    assert len(service.list_custom_models()) == 1
    assert service.list_custom_models()[0]["name"] == "test-model"
    
    # Update
    service.upsert_custom_model({"name": "test-model", "api_key": "****", "base_url": "http://test"})
    models = service.list_custom_models()
    assert models[0]["api_key"] == "key1"
    assert models[0]["base_url"] == "http://test"
    
    # Delete
    service.delete_custom_model("test-model")
    assert len(service.list_custom_models()) == 0

def test_doc_access_validation(temp_config_file):
    service = ConfigService(str(temp_config_file))
    
    doc_access = {
        "allow_roots": ["/path/a", "", None, 123],
        "deny_roots": ["/path/b"]
    }
    service.update_doc_access(doc_access)
    
    result = service.get_doc_access()
    assert result["allow_roots"] == ["/path/a"]
    assert result["deny_roots"] == ["/path/b"]
