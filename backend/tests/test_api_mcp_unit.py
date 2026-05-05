import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from app.main import app
from app.mcp.templates import render_template
from pathlib import Path

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_mcp_manager():
    with patch("app.api.mcp.mcp_manager") as mock:
        # Patch the CONFIG_PATH that was imported in app.api.mcp
        with patch("app.api.mcp.CONFIG_PATH", "/tmp/mcp_config.json"):
            mock.config_path = "/tmp/mcp_config.json"
            yield mock

def test_list_configs(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [{"name": "server1"}]
    response = client.get("/api/mcp/")
    assert response.status_code == 200
    assert response.json() == [{"name": "server1"}]

@pytest.mark.asyncio
async def test_list_tools(client, mock_mcp_manager):
    with patch("app.api.mcp.tool_registry") as mock_registry:
        mock_registry.get_all_available_tools_metadata = AsyncMock(return_value=[{"name": "tool1"}])
        response = client.get("/api/mcp/tools")
        assert response.status_code == 200
        assert response.json() == [{"name": "tool1"}]

def test_get_status(client, mock_mcp_manager):
    mock_mcp_manager.get_status.return_value = {"server1": "connected"}
    response = client.get("/api/mcp/status")
    assert response.status_code == 200
    assert response.json() == {"server1": "connected"}

def test_list_templates(client, mock_mcp_manager):
    response = client.get("/api/mcp/templates")
    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == "jira-company" for item in body)
    assert any(item["id"] == "confluence-company" for item in body)

def test_example_config_documents_token_only_jira_onboarding_contract(client, mock_mcp_manager):
    example_path = Path(__file__).resolve().parents[1] / "data" / "mcp_configs.json.example"
    payload = json.loads(example_path.read_text(encoding="utf-8"))

    jira_entry = next(item for item in payload if item["name"] == "company-jira")

    assert jira_entry["enabled"] is False
    assert jira_entry["args"] == ["-y", "your-company-jira-mcp-package"]
    assert jira_entry["env"]["JIRA_BASE_URL"] == "https://jira.company.internal"
    assert jira_entry["env"]["JIRA_TOKEN"] == "${JIRA_TOKEN}"
    assert "JIRA_USERNAME" not in jira_entry["env"]
    assert jira_entry["env"]["JIRA_ALLOWED_PROJECTS"] == "YUE"
    assert jira_entry["env"]["JIRA_DEFAULT_JQL"] == "project = YUE ORDER BY updated DESC"
    assert jira_entry["env"]["JIRA_READ_ONLY"] == "true"

def test_example_config_includes_streamable_http_entry(client, mock_mcp_manager):
    example_path = Path(__file__).resolve().parents[1] / "data" / "mcp_configs.json.example"
    payload = json.loads(example_path.read_text(encoding="utf-8"))

    remote_entry = next(item for item in payload if item["name"] == "example-remote-server")

    assert remote_entry["transport"] == "streamable_http"
    assert remote_entry["url"] == "https://mcp.example.com/stream"
    assert remote_entry["enabled"] is False
    assert remote_entry["headers"]["Authorization"] == "${MCP_REMOTE_TOKEN}"

def test_update_configs_success(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = []
    m = mock_open()
    with patch("app.api.mcp.open", m):
        new_config = {
            "name": "new_server",
            "command": "node",
            "args": ["server.js"],
            "transport": "stdio"
        }
        response = client.post("/api/mcp/", json=[new_config])
        assert response.status_code == 200
        # Check if json.dump was called
        m.assert_called_with(mock_mcp_manager.config_path, 'w')

def test_update_configs_invalid(client, mock_mcp_manager):
    response = client.post("/api/mcp/", json=[{"name": "missing_command"}])
    assert response.status_code == 400

def test_update_configs_defaults_missing_transport_to_stdio(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = []
    m = mock_open()
    with patch("app.api.mcp.open", m):
        response = client.post(
            "/api/mcp/",
            json=[{"name": "legacy_stdio", "command": "node", "args": ["server.js"]}],
        )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["transport"] == "stdio"
    assert body[0]["command"] == "node"

def test_update_configs_accepts_streamable_http_with_url(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = []
    m = mock_open()
    with patch("app.api.mcp.open", m):
        response = client.post(
            "/api/mcp/",
            json=[{"name": "remote_mcp", "transport": "streamable_http", "url": "https://mcp.example.com"}],
        )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["transport"] == "streamable_http"
    assert body[0]["url"] == "https://mcp.example.com"

def test_update_configs_preserves_timeout_and_min_version(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = []
    m = mock_open()
    with patch("app.api.mcp.open", m):
        response = client.post(
            "/api/mcp/",
            json=[
                {
                    "name": "remote_mcp",
                    "transport": "streamable_http",
                    "url": "https://mcp.example.com",
                    "timeout": 12.5,
                    "min_version": "2026.1.0",
                }
            ],
        )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["timeout"] == 12.5
    assert body[0]["min_version"] == "2026.1.0"

def test_update_configs_rejects_stdio_without_command(client, mock_mcp_manager):
    response = client.post(
        "/api/mcp/",
        json=[{"name": "bad_stdio", "transport": "stdio"}],
    )
    assert response.status_code == 400

def test_update_configs_rejects_streamable_http_without_url(client, mock_mcp_manager):
    response = client.post(
        "/api/mcp/",
        json=[{"name": "bad_remote", "transport": "streamable_http"}],
    )
    assert response.status_code == 400

def test_update_configs_rejects_stale_url_for_stdio(client, mock_mcp_manager):
    response = client.post(
        "/api/mcp/",
        json=[{"name": "bad_stdio", "transport": "stdio", "command": "node", "url": "https://mcp.example.com"}],
    )
    assert response.status_code == 400

def test_update_configs_rejects_stale_command_for_streamable_http(client, mock_mcp_manager):
    response = client.post(
        "/api/mcp/",
        json=[{"name": "bad_remote", "transport": "streamable_http", "url": "https://mcp.example.com", "command": "node"}],
    )
    assert response.status_code == 400

def test_update_configs_switching_transport_drops_stale_fields(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [
        {
            "name": "switchable",
            "transport": "stdio",
            "command": "node",
            "args": ["server.js"],
            "enabled": True,
        }
    ]
    m = mock_open()
    with patch("app.api.mcp.open", m):
        response = client.post(
            "/api/mcp/",
            json=[{"name": "switchable", "transport": "streamable_http", "url": "https://mcp.example.com"}],
        )
    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "name": "switchable",
            "transport": "streamable_http",
            "url": "https://mcp.example.com",
            "enabled": True,
        }
    ]

def test_validate_template_success(client, mock_mcp_manager):
    with patch("app.api.mcp.shutil.which", return_value="/usr/bin/npx"):
        response = client.post(
            "/api/mcp/validate",
            json={
                "template_id": "jira-company",
                "values": {
                    "serverName": "corp-jira",
                    "command": "npx",
                    "argsJson": '["-y","corp-jira-mcp"]',
                    "baseUrl": "https://jira.company.internal",
                    "baseUrlEnvKey": "JIRA_BASE_URL",
                    "username": "alice@example.com",
                    "usernameEnvKey": "JIRA_USERNAME",
                    "secretEnvVar": "JIRA_TOKEN",
                    "tokenEnvKey": "JIRA_TOKEN",
                    "extraEnvJson": '{"JIRA_PROJECT":"CORE"}',
                },
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["rendered_config"]["name"] == "corp-jira"
    assert body["rendered_config"]["env"]["JIRA_TOKEN"] == "${JIRA_TOKEN}"
    assert body["rendered_config"]["env"]["JIRA_PROJECT"] == "CORE"

def test_render_jira_template_omits_username_env_when_username_blank():
    result = render_template(
        "jira-company",
        {
            "serverName": "corp-jira",
            "command": "npx",
            "argsJson": '["-y","your-company-jira-mcp-package"]',
            "baseUrl": "https://jira.company.internal",
            "baseUrlEnvKey": "JIRA_BASE_URL",
            "username": "",
            "usernameEnvKey": "JIRA_USERNAME",
            "secretEnvVar": "JIRA_TOKEN",
            "tokenEnvKey": "JIRA_TOKEN",
            "extraEnvJson": '{"JIRA_READ_ONLY":"true","JIRA_ALLOWED_PROJECTS":"YUE"}',
        },
    )

    assert result.rendered_config["name"] == "corp-jira"
    assert result.rendered_config["env"]["JIRA_BASE_URL"] == "https://jira.company.internal"
    assert result.rendered_config["env"]["JIRA_TOKEN"] == "${JIRA_TOKEN}"
    assert result.rendered_config["env"]["JIRA_READ_ONLY"] == "true"
    assert result.rendered_config["env"]["JIRA_ALLOWED_PROJECTS"] == "YUE"
    assert "JIRA_USERNAME" not in result.rendered_config["env"]

def test_validate_template_invalid_json(client, mock_mcp_manager):
    with patch("app.api.mcp.shutil.which", return_value="/usr/bin/npx"):
        response = client.post(
            "/api/mcp/validate",
            json={
                "template_id": "custom-company-mcp",
                "values": {
                    "serverName": "internal",
                    "command": "npx",
                    "argsJson": "{",
                    "envJson": "{}",
                },
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "Args must be valid JSON" in body["error"]

def test_validate_template_streamable_http_skips_command_lookup(client, mock_mcp_manager):
    with patch("app.api.mcp.render_template") as mock_render, patch("app.api.mcp.shutil.which") as mock_which:
        mock_render.return_value = MagicMock(
            rendered_config={
                "name": "remote_mcp",
                "transport": "streamable_http",
                "url": "https://mcp.example.com",
            },
            warnings=[],
        )
        response = client.post(
            "/api/mcp/validate",
            json={"template_id": "jira-company", "values": {}},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    mock_which.assert_not_called()

@pytest.mark.asyncio
async def test_reload_mcp(client, mock_mcp_manager):
    mock_mcp_manager.cleanup = AsyncMock()
    mock_mcp_manager.initialize = AsyncMock()
    response = client.post("/api/mcp/reload")
    assert response.status_code == 200
    assert response.json() == {"status": "reloaded"}
    mock_mcp_manager.cleanup.assert_called_once()
    mock_mcp_manager.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_delete_config_success(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [{"name": "target"}, {"name": "other"}]
    m = mock_open()
    with patch("app.api.mcp.open", m):
        mock_mcp_manager.cleanup = AsyncMock()
        mock_mcp_manager.initialize = AsyncMock()
        response = client.delete("/api/mcp/target")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        m.assert_called_with(mock_mcp_manager.config_path, 'w')

def test_delete_config_not_found(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [{"name": "other"}]
    response = client.delete("/api/mcp/non_existent")
    assert response.status_code == 404


# --- Smart Paste parse endpoint tests ---


def test_parse_endpoint_returns_rule_result(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": True}
        response = client.post("/api/mcp/parse", json={"raw_text": "npx -y @company/mcp"})
        assert response.status_code == 200
        assert response.json()["parse_mode"] == "rule"


def test_parse_endpoint_returns_503_when_feature_disabled_and_rule_fails(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": False}
        response = client.post("/api/mcp/parse", json={"raw_text": "hello world not a config"})
        assert response.status_code == 503


def test_parse_endpoint_rejects_empty_input(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": True}
        response = client.post("/api/mcp/parse", json={"raw_text": ""})
        assert response.status_code == 422


def test_parse_endpoint_returns_rule_result_even_when_flag_disabled(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": False}
        response = client.post("/api/mcp/parse", json={"raw_text": "npx -y @company/mcp"})
        assert response.status_code == 200
        assert response.json()["parse_mode"] == "rule"


def test_parse_endpoint_returns_error_when_flag_disabled_and_rule_fails(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": False}
        response = client.post(
            "/api/mcp/parse",
            json={"raw_text": "用自然语言描述的一个 MCP 配置，规则解析无法处理"}
        )
        assert response.status_code == 503
        assert "AI" in response.json()["detail"].lower() or "解析" in response.json()["detail"]
