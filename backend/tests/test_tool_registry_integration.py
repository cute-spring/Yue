import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from app.mcp.registry import ToolRegistry
from app.mcp.base import McpTool, BuiltinTool
from app.mcp.schema_translator import to_provider_schema

@pytest.fixture
def mock_mcp_manager():
    manager = MagicMock()
    manager.sessions = {}
    manager.last_errors = {}
    manager._get_builtin_tools_metadata.return_value = [
        {
            "id": "builtin:test_builtin",
            "name": "test_builtin",
            "description": "A test builtin tool",
            "input_schema": {"type": "object", "properties": {"arg": {"type": "string"}}}
        }
    ]
    
    async def mock_handler(ctx, arg):
        return f"Builtin handled: {arg}"
        
    manager._get_builtin_tools.return_value = [
        ("test_builtin", mock_handler)
    ]
    return manager

@pytest.fixture
def registry(mock_mcp_manager):
    return ToolRegistry(mock_mcp_manager)

@pytest.mark.asyncio
async def test_registry_no_agent(registry):
    """Test registry behavior when no agent ID is provided."""
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = None
        tools = await registry.get_tools_for_agent(None)
        assert tools == []

@pytest.mark.asyncio
async def test_registry_agent_no_tools(registry):
    """Test registry behavior when agent has no tools enabled."""
    mock_agent = MagicMock()
    mock_agent.enabled_tools = []
    
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_tools_for_agent("agent-1")
        assert tools == []

@pytest.mark.asyncio
async def test_registry_builtin_tool_authorization(registry, mock_mcp_manager):
    """Test that builtin tools are correctly authorized."""
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin"]
    
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_tools_for_agent("agent-1")
        
        assert len(tools) == 1
        assert isinstance(tools[0], BuiltinTool)
        assert tools[0].name == "test_builtin"

@pytest.mark.asyncio
async def test_registry_mcp_tool_authorization(registry, mock_mcp_manager):
    """Test that MCP tools are correctly authorized."""
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["server1:test_mcp_tool"]
    
    mock_session = AsyncMock()
    mock_session.is_closed = False
    mock_result = MagicMock()
    mock_tool_def = MagicMock()
    mock_tool_def.name = "test_mcp_tool"
    mock_tool_def.description = "An MCP tool"
    mock_tool_def.inputSchema = {"type": "object"}
    mock_result.tools = [mock_tool_def]
    mock_session.list_tools.return_value = mock_result
    
    mock_mcp_manager.sessions = {"server1": mock_session}
    
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_tools_for_agent("agent-1")
        
        assert len(tools) == 1
        assert isinstance(tools[0], McpTool)
        assert tools[0].name == "test_mcp_tool"
        assert tools[0].server_name == "server1"

@pytest.mark.asyncio
async def test_registry_mixed_tools(registry, mock_mcp_manager):
    """Test that both builtin and MCP tools can be authorized together."""
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin", "server1:test_mcp_tool"]
    
    mock_session = AsyncMock()
    mock_session.is_closed = False
    mock_result = MagicMock()
    mock_tool_def = MagicMock()
    mock_tool_def.name = "test_mcp_tool"
    mock_tool_def.description = "An MCP tool"
    mock_tool_def.inputSchema = {"type": "object"}
    mock_result.tools = [mock_tool_def]
    mock_session.list_tools.return_value = mock_result
    mock_mcp_manager.sessions = {"server1": mock_session}
    
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_tools_for_agent("agent-1")
        
        assert len(tools) == 2
        names = [t.name for t in tools]
        assert "test_builtin" in names
        assert "test_mcp_tool" in names

@pytest.mark.asyncio
async def test_registry_pydantic_ai_conversion(registry, mock_mcp_manager):
    """Test that tools are correctly converted to Pydantic AI Tool objects with proper names."""
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin", "server-1:test_mcp_tool"]
    
    mock_session = AsyncMock()
    mock_session.is_closed = False
    mock_result = MagicMock()
    mock_tool_def = MagicMock()
    mock_tool_def.name = "test_mcp_tool"
    mock_tool_def.description = "An MCP tool"
    mock_tool_def.inputSchema = {"type": "object", "properties": {}}
    mock_result.tools = [mock_tool_def]
    mock_session.list_tools.return_value = mock_result
    mock_mcp_manager.sessions = {"server-1": mock_session}
    
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        pydantic_tools = await registry.get_pydantic_ai_tools_for_agent("agent-1")
        
        assert len(pydantic_tools) == 2
        
        builtin_tool = next(t for t in pydantic_tools if t.name == "test_builtin")
        assert builtin_tool is not None
        
        mcp_tool = next(t for t in pydantic_tools if t.name == "mcp__server-1__test_mcp_tool")
        assert mcp_tool is not None

@pytest.mark.asyncio
async def test_registry_shadow_mode_compare(registry, mock_mcp_manager, monkeypatch):
    monkeypatch.setenv("MCP_TOOL_SHADOW_MODE", "1")
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin"]
    mock_mcp_manager.get_available_tools = AsyncMock(return_value=[
        {
            "id": "builtin:test_builtin",
            "name": "test_builtin",
            "description": "A test builtin tool",
            "server": "builtin",
            "input_schema": {"type": "object", "properties": {"arg": {"type": "string"}}}
        }
    ])
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_tools_for_agent("agent-1")
        assert len(tools) == 1
        mock_mcp_manager.get_available_tools.assert_awaited()


@pytest.mark.asyncio
async def test_registry_provider_schema_prepare(registry, mock_mcp_manager):
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin"]
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_pydantic_ai_tools_for_agent("agent-1", provider="openai")
        tool = tools[0]
        tool_def = await tool.prepare_tool_def(MagicMock())
        expected = to_provider_schema("openai", {"type": "object", "properties": {"arg": {"type": "string"}}})
        assert tool_def.parameters_json_schema == expected

@pytest.mark.asyncio
async def test_registry_tool_success_no_hint(registry, mock_mcp_manager):
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin"]
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_pydantic_ai_tools_for_agent("agent-1")
        tool = tools[0]
        import inspect
        sig = inspect.signature(tool.function)
        ArgsModel = sig.parameters["args"].annotation
        args = ArgsModel(arg="ok")
        result = await tool.function(MagicMock(), args)
        assert result == "Builtin handled: ok"
        assert "error_code" not in result

@pytest.mark.asyncio
async def test_registry_tool_error_structured_hint():
    manager = MagicMock()
    manager.sessions = {}
    manager.last_errors = {}
    manager._get_builtin_tools_metadata.return_value = [
        {
            "id": "builtin:test_builtin",
            "name": "test_builtin",
            "description": "A test builtin tool",
            "input_schema": {"type": "object", "properties": {"arg": {"type": "string"}}}
        }
    ]

    async def error_handler(ctx, arg):
        raise FileNotFoundError("/private/secret/file.txt")

    manager._get_builtin_tools.return_value = [
        ("test_builtin", error_handler)
    ]
    registry = ToolRegistry(manager)
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:test_builtin"]
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_pydantic_ai_tools_for_agent("agent-1")
        tool = tools[0]
        import inspect
        sig = inspect.signature(tool.function)
        ArgsModel = sig.parameters["args"].annotation
        args = ArgsModel(arg="nope")
        result = await tool.function(MagicMock(), args)
        payload = json.loads(result)
        assert set(payload.keys()) == {"error_code", "message", "hint"}
        assert payload["error_code"] == "tool_not_found"
        assert payload["hint"]
        assert "/private" not in payload["message"]
        assert "/private" not in payload["hint"]
