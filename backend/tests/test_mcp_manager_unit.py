from typing import Any
import pytest
import os
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from app.mcp.manager import McpManager
from app.mcp.base import McpTool, BuiltinTool
from app.mcp.registry import ToolRegistry
from app.mcp.builtin import builtin_tool_registry

@pytest.fixture
def mcp_manager():
    # Reset singleton for each test
    McpManager._instance = None
    manager = McpManager()
    manager.config_path = "test_mcp_configs.json"
    manager.sessions = {} # Ensure sessions are empty
    return manager

@pytest.fixture
def test_config():
    return [
        {
            "name": "test-server",
            "enabled": True,
            "command": "node",
            "args": ["server.js"],
            "transport": "stdio"
        }
    ]

def test_singleton():
    m1 = McpManager()
    m2 = McpManager()
    assert m1 is m2

def test_load_config_empty(mcp_manager):
    if os.path.exists(mcp_manager.config_path):
        os.remove(mcp_manager.config_path)
    assert mcp_manager.load_config() == []

def test_load_config_valid(mcp_manager, test_config):
    with open(mcp_manager.config_path, 'w') as f:
        json.dump(test_config, f)
    try:
        assert mcp_manager.load_config() == test_config
    finally:
        os.remove(mcp_manager.config_path)

@pytest.mark.asyncio
async def test_connect_to_server_stdio(mcp_manager, test_config):
    with patch("app.mcp.manager.stdio_client") as mock_stdio, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:
        
        # Mock stdio_client
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock ClientSession
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        config = test_config[0]
        session = await mcp_manager.connect_to_server(config)
        
        assert session == mock_session
        assert "test-server" in mcp_manager.sessions
        mock_session.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup(mcp_manager):
    mcp_manager.sessions["test"] = AsyncMock()
    with patch.object(mcp_manager.exit_stack, "aclose", new_callable=AsyncMock) as mock_aclose:
        await mcp_manager.cleanup()
        mock_aclose.assert_called_once()
        assert len(mcp_manager.sessions) == 0

def test_redact_configs(mcp_manager):
    configs = [{
        "name": "s1",
        "env": {"API_KEY": "secret", "OTHER": "public"}
    }]
    redacted = mcp_manager._redact_configs(configs)
    assert redacted[0]["env"]["API_KEY"] == "****"
    assert redacted[0]["env"]["OTHER"] == "public"

@pytest.mark.asyncio
async def test_get_available_tools(mcp_manager):
    mock_session = AsyncMock()
    mock_session.is_closed = False
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "desc"
    mock_tool.inputSchema = {}
    
    mock_result = MagicMock()
    mock_result.tools = [mock_tool]
    mock_session.list_tools.return_value = mock_result
    
    mcp_manager.sessions = {
        "srv1": mock_session
    }
    
    with patch("app.mcp.manager.builtin_tool_registry.get_all_metadata") as mock_meta:
        mock_meta.return_value = [{"id": "builtin:test", "name": "test", "server": "builtin"}]
        tools = await mcp_manager.get_available_tools()
        assert len(tools) >= 2
        assert any(t["id"] == "srv1:test_tool" for t in tools)
        assert any(t["id"] == "builtin:test" for t in tools)

@pytest.mark.asyncio
async def test_get_status(mcp_manager, test_config):
    with open(mcp_manager.config_path, 'w') as f:
        json.dump(test_config, f)
    
    try:
        mcp_manager.sessions["test-server"] = MagicMock()
        status = mcp_manager.get_status()
        assert status[0]["name"] == "test-server"
        assert status[0]["connected"] is True
    finally:
        os.remove(mcp_manager.config_path)

@pytest.mark.asyncio
async def test_placeholder_resolution(mcp_manager):
    config = {
        "name": "test",
        "command": "node",
        "args": ["${PROJECT_ROOT}/test.js"],
        "transport": "stdio"
    }
    with patch("app.mcp.manager.stdio_client") as mock_stdio, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:
        
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        
        await mcp_manager.connect_to_server(config)
        
        # Check if PROJECT_ROOT was replaced
        call_args = mock_stdio.call_args[0][0]
        assert "${PROJECT_ROOT}" not in call_args.args[0]
        assert "Yue" in call_args.args[0]

@pytest.mark.asyncio
async def test_proxy_propagation(mcp_manager):
    config = {
        "name": "test",
        "command": "node",
        "args": [],
        "transport": "stdio"
    }
    with patch("app.mcp.manager.config_service") as mock_config_service, \
         patch("app.mcp.manager.stdio_client") as mock_stdio, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:
        
        mock_config_service.get_llm_config.return_value = {
            "proxy_url": "http://proxy:8080",
            "no_proxy": "google.com"
        }
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        
        await mcp_manager.connect_to_server(config)
        
        call_args = mock_stdio.call_args[0][0]
        assert call_args.env["HTTP_PROXY"] == "http://proxy:8080"
        assert "google.com" in call_args.env["NO_PROXY"]
        assert "127.0.0.1" in call_args.env["NO_PROXY"]

@pytest.mark.asyncio
async def test_get_tools_for_agent(mcp_manager):
    # Mock session
    mock_session = AsyncMock()
    
    # Use a real-ish object for tool to avoid MagicMock .name issues
    class MockTool:
        def __init__(self, name, description, inputSchema):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema
            
    mock_tool = MockTool(
        name="test_tool",
        description="desc",
        inputSchema={"type": "object", "properties": {"arg1": {"type": "string"}}}
    )
    
    mock_result = MagicMock()
    mock_result.tools = [mock_tool]
    mock_session.list_tools.return_value = mock_result
    mock_session.is_closed = False
    mcp_manager.sessions["server1"] = mock_session
    
    # Initialize registry
    registry = ToolRegistry(mcp_manager)
    
    # Mock agent_store
    with patch("app.mcp.registry.agent_store") as mock_agent_store:
        mock_agent = MagicMock()
        mock_agent.enabled_tools = ["server1:test_tool"]
        mock_agent_store.get_agent.return_value = mock_agent
        
        tools = await registry.get_pydantic_ai_tools_for_agent("agent-id")
        
        assert len(tools) > 0
        # Check if the generated tool has the right name (mcp__server__tool)
        assert any(t.name == "mcp__server1__test_tool" for t in tools)

def test_map_json_type():
    # Test through McpTool/BuiltinTool indirectly or just test the logic in McpTool
    tool = McpTool("srv", AsyncMock(), "name", "desc", {})
    assert tool._map_json_type("string") == str
    assert tool._map_json_type("integer") == int
    assert tool._map_json_type("number") == float
    assert tool._map_json_type("boolean") == bool
    assert tool._map_json_type("object") == dict
    assert tool._map_json_type("array") == list
    assert tool._map_json_type("unknown") == Any

@pytest.mark.asyncio
async def test_convert_tool_no_properties(mcp_manager):
    mock_session = AsyncMock()
    # Tool with no properties
    mcp_tool = McpTool(
        server_name="srv",
        session=mock_session,
        name="simple_tool",
        description="no args",
        parameters={"type": "object"}
    )
    
    tool = mcp_tool.to_pydantic_ai_tool()
    assert tool.name == "simple_tool"
    assert tool.description == "no args"

@pytest.mark.asyncio
async def test_refresh_tools_success(mcp_manager):
    # Mock config
    config = [
        {"name": "srv1", "command": "node", "args": ["srv1.js"], "enabled": True}
    ]
    
    with patch("app.mcp.manager.McpManager.load_config", return_value=config), \
         patch("app.mcp.manager.stdio_client") as mock_stdio, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:
        
        # Mock stdio_client context manager
        mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        
        # Mock ClientSession context manager
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.initialize = AsyncMock()
        
        await mcp_manager.initialize()
        
        assert "srv1" in mcp_manager.sessions
        mock_session.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_convert_tool_image_content(mcp_manager):
    mock_session = AsyncMock()
    mcp_tool = McpTool(
        server_name="srv",
        session=mock_session,
        name="img_tool",
        description="desc",
        parameters={"type": "object"}
    )
    
    tool = mcp_tool.to_pydantic_ai_tool()
    
    # Mock result with image content
    mock_content = MagicMock()
    mock_content.type = "image"
    mock_result = MagicMock()
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result
    
    ctx = MagicMock()
    import inspect
    sig = inspect.signature(tool.function)
    ArgsModel = sig.parameters['args'].annotation
    args = ArgsModel()
    
    result = await tool.function(ctx, args)
    assert "[image]" in result

@pytest.mark.asyncio
async def test_initialize_connect_error(mcp_manager):
    config = [{"name": "test-server", "enabled": True, "command": "node"}]
    with patch.object(mcp_manager, "load_config", return_value=config), \
         patch.object(mcp_manager, "_connect_to_server_unlocked", side_effect=Exception("Connection failed")):
        await mcp_manager.initialize()
        assert mcp_manager.last_errors["test-server"] == "Connection failed"

@pytest.mark.asyncio
async def test_cleanup_error(mcp_manager):
    mcp_manager.exit_stack = MagicMock()
    mcp_manager.exit_stack.aclose = AsyncMock(side_effect=Exception("Cleanup error"))
    # Should not raise
    await mcp_manager.cleanup()
    assert mcp_manager.sessions == {}

def test_load_config_error(mcp_manager):
    with patch("builtins.open", side_effect=Exception("Read error")):
        with patch("os.path.exists", return_value=True):
            configs = mcp_manager.load_config()
            assert configs == []

@pytest.mark.asyncio
async def test_connect_to_server_existing_session(mcp_manager):
    mock_session = MagicMock()
    mock_session.is_closed = False
    mcp_manager.sessions["existing"] = mock_session
    
    config = {"name": "existing"}
    session = await mcp_manager.connect_to_server(config)
    assert session == mock_session

@pytest.mark.asyncio
async def test_connect_to_server_existing_closed_session(mcp_manager):
    mock_session = MagicMock()
    mock_session.is_closed = True
    mcp_manager.sessions["closed"] = mock_session
    
    config = {"name": "closed", "transport": "stdio", "command": "node"}
    with patch("app.mcp.manager.stdio_client") as mock_stdio, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:
        
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        
        await mcp_manager.connect_to_server(config)
        assert "closed" in mcp_manager.sessions
        assert mcp_manager.sessions["closed"] != mock_session

@pytest.mark.asyncio
async def test_convert_tool_wrapper_execution(mcp_manager):
    mock_session = AsyncMock()
    mcp_tool = McpTool(
        server_name="srv",
        session=mock_session,
        name="exec_tool",
        description="desc",
        parameters={"type": "object", "properties": {"cmd": {"type": "string"}}}
    )
    
    tool = mcp_tool.to_pydantic_ai_tool()
    
    # Mock result from call_tool
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = "output"
    mock_result = MagicMock()
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result
    
    # Execute the tool
    ctx = MagicMock()
    import inspect
    sig = inspect.signature(tool.function)
    ArgsModel = sig.parameters['args'].annotation
    args = ArgsModel(cmd="ls")
    
    result = await tool.function(ctx, args)
    assert result == "output"
    mock_session.call_tool.assert_called_once_with("exec_tool", arguments={"cmd": "ls"})

def test_redact_configs_case_insensitivity(mcp_manager):
    configs = [{
        "name": "s1",
        "env": {"api_key": "secret", "PASSword": "123", "normal": "val"}
    }]
    redacted = mcp_manager._redact_configs(configs)
    assert redacted[0]["env"]["api_key"] == "****"
    assert redacted[0]["env"]["PASSword"] == "****"
    assert redacted[0]["env"]["normal"] == "val"

@pytest.mark.asyncio
async def test_initialize_connects_streamable_http_server(mcp_manager, monkeypatch):
    monkeypatch.setenv("MCP_API_TOKEN", "test-token")
    config = [{
        "name": "remote-server",
        "transport": "streamable_http",
        "url": "https://example.com/mcp",
        "headers": {
            "Authorization": "Bearer ${MCP_API_TOKEN}",
            "X-Trace": "public"
        },
        "enabled": True,
        "timeout": 12.5
    }]

    with patch.object(mcp_manager, "load_config", return_value=config), \
         patch("app.mcp.manager.create_mcp_http_client", create=True) as mock_http_client_factory, \
         patch("app.mcp.manager.streamable_http_client", create=True) as mock_streamable_http, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:

        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client_factory.return_value = mock_http_client
        mock_streamable_http.return_value.__aenter__.return_value = (
            AsyncMock(),
            AsyncMock(),
            MagicMock(return_value="session-id"),
        )
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        await mcp_manager.initialize()

        assert "remote-server" in mcp_manager.sessions
        assert mcp_manager.sessions["remote-server"] == mock_session
        assert mcp_manager.last_errors.get("remote-server") is None
        mock_http_client_factory.assert_called_once()
        headers = mock_http_client_factory.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["X-Trace"] == "public"
        mock_streamable_http.assert_called_once_with(
            "https://example.com/mcp",
            http_client=mock_http_client,
        )
        mock_session.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_streamable_http_headers_can_resolve_from_config_env(mcp_manager, monkeypatch):
    monkeypatch.setenv("HOST_REMOTE_TOKEN", "config-derived-token")
    config = [{
        "name": "remote-server",
        "transport": "streamable_http",
        "url": "https://example.com/mcp",
        "env": {
            "MCP_REMOTE_TOKEN": "${HOST_REMOTE_TOKEN}",
        },
        "headers": {
            "Authorization": "Bearer ${MCP_REMOTE_TOKEN}",
        },
        "enabled": True,
    }]

    with patch.object(mcp_manager, "load_config", return_value=config), \
         patch("app.mcp.manager.create_mcp_http_client", create=True) as mock_http_client_factory, \
         patch("app.mcp.manager.streamable_http_client", create=True) as mock_streamable_http, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls:

        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client_factory.return_value = mock_http_client
        mock_streamable_http.return_value.__aenter__.return_value = (
            AsyncMock(),
            AsyncMock(),
            MagicMock(return_value="session-id"),
        )
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        await mcp_manager.initialize()

        headers = mock_http_client_factory.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer config-derived-token"

@pytest.mark.asyncio
async def test_streamable_http_registers_http_client_with_exit_stack(mcp_manager):
    config = {
        "name": "remote-server",
        "transport": "streamable_http",
        "url": "https://example.com/mcp",
        "headers": {"Authorization": "Bearer ${MCP_API_TOKEN}"},
    }

    mock_http_client = MagicMock()
    mock_read = AsyncMock()
    mock_write = AsyncMock()
    mock_session = AsyncMock()

    with patch("app.mcp.manager.create_mcp_http_client", return_value=mock_http_client), \
         patch("app.mcp.manager.streamable_http_client", create=True) as mock_streamable_http, \
         patch("app.mcp.manager.ClientSession") as mock_session_cls, \
         patch.object(mcp_manager.exit_stack, "enter_async_context", new_callable=AsyncMock) as mock_enter:
        mock_streamable_http.return_value = "transport-context"
        mock_session_cls.return_value = "session-context"
        mock_enter.side_effect = [
            mock_http_client,
            (mock_read, mock_write, MagicMock(return_value="session-id")),
            mock_session,
        ]

        await mcp_manager.connect_to_server(config)

    assert mock_enter.await_count == 3
    assert mock_enter.await_args_list[0].args[0] is mock_http_client
    assert mock_enter.await_args_list[1].args[0] == "transport-context"
    assert mock_enter.await_args_list[2].args[0] == "session-context"

@pytest.mark.asyncio
async def test_initialize_and_exit_stack_close_streamable_http_in_same_task(mcp_manager):
    class TaskBoundContext:
        def __init__(self, value):
            self.value = value
            self.enter_task = None

        async def __aenter__(self):
            self.enter_task = asyncio.current_task()
            return self.value

        async def __aexit__(self, exc_type, exc, tb):
            if asyncio.current_task() is not self.enter_task:
                raise RuntimeError("entered and exited in different tasks")
            return False

    config = [{
        "name": "remote-server",
        "transport": "streamable_http",
        "url": "https://example.com/mcp",
        "enabled": True,
    }]
    init_result = MagicMock()
    init_result.serverInfo = MagicMock(name="bing-cn-search", version="1.9.4")
    mock_session = AsyncMock()
    mock_session.initialize.return_value = init_result

    with patch.object(mcp_manager, "load_config", return_value=config), \
         patch("app.mcp.manager.create_mcp_http_client", return_value=TaskBoundContext(MagicMock())), \
         patch("app.mcp.manager.streamable_http_client", return_value=TaskBoundContext((AsyncMock(), AsyncMock(), MagicMock()))), \
         patch("app.mcp.manager.ClientSession", return_value=TaskBoundContext(mock_session)):
        await mcp_manager.initialize()
        await mcp_manager.exit_stack.aclose()

def test_redact_configs_masks_secret_headers(mcp_manager):
    configs = [{
        "name": "remote-server",
        "transport": "streamable_http",
        "headers": {
            "Authorization": "Bearer secret-token",
            "X-Api-Key": "super-secret",
            "X-Trace": "public"
        }
    }]

    redacted = mcp_manager._redact_configs(configs)

    assert redacted[0]["headers"]["Authorization"] == "****"
    assert redacted[0]["headers"]["X-Api-Key"] == "****"
    assert redacted[0]["headers"]["X-Trace"] == "public"

def test_get_status_defaults_missing_transport_to_stdio_and_exposes_last_error(mcp_manager):
    legacy_config = [{
        "name": "legacy-server",
        "enabled": True,
        "command": "node",
        "args": ["server.js"]
    }]

    with open(mcp_manager.config_path, "w") as f:
        json.dump(legacy_config, f)

    try:
        mcp_manager.last_errors["legacy-server"] = "Connection timeout"
        status = mcp_manager.get_status()
        assert status == [{
            "name": "legacy-server",
            "enabled": True,
            "connected": False,
            "transport": "stdio",
            "last_error": "Connection timeout",
            "server_name": None,
            "version": None,
        }]
    finally:
        os.remove(mcp_manager.config_path)
