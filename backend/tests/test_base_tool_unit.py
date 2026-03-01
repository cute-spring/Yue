import pytest
from app.mcp.base import BaseTool
from app.mcp.schema_translator import to_provider_schema
from pydantic_ai import RunContext
from typing import Any, Dict

class MockTool(BaseTool):
    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return f"executed with {args}"

@pytest.mark.asyncio
async def test_base_tool_schema_generation():
    params = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results"}
        },
        "required": ["query"]
    }
    tool = MockTool(name="test_tool", description="A test tool", parameters=params)
    pydantic_tool = tool.to_pydantic_ai_tool()
    
    assert pydantic_tool.name == "test_tool"
    assert pydantic_tool.description == "A test tool"
    
    import inspect
    sig = inspect.signature(pydantic_tool.function)
    ArgsModel = sig.parameters['args'].annotation
    
    schema = ArgsModel.model_json_schema()
    assert schema["type"] == "object"
    assert "query" in schema["properties"]
    assert "limit" in schema["properties"]
    assert "query" in schema["required"]
    assert schema["properties"]["query"]["type"] == "string"
    assert schema["properties"]["limit"]["type"] == "integer"

@pytest.mark.asyncio
async def test_base_tool_execution():
    params = {
        "type": "object",
        "properties": {
            "val": {"type": "string"}
        }
    }
    tool = MockTool(name="test_tool", description="desc", parameters=params)
    pydantic_tool = tool.to_pydantic_ai_tool()
    
    from unittest.mock import MagicMock
    ctx = MagicMock(spec=RunContext)
    
    import inspect
    sig = inspect.signature(pydantic_tool.function)
    ArgsModel = sig.parameters['args'].annotation
    args = ArgsModel(val="hello")
    
    result = await pydantic_tool.function(ctx, args)
    assert result == "executed with {'val': 'hello'}"

@pytest.mark.asyncio
async def test_base_tool_advanced_schema():
    """Test mapping of complex JSON schema types (enum, array, etc.)."""
    from typing import get_args
    params = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["fast", "slow"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "optional_val": {"type": ["string", "null"]}
        }
    }
    tool = MockTool(name="advanced_tool", description="desc", parameters=params)
    pydantic_tool = tool.to_pydantic_ai_tool()
    
    import inspect
    sig = inspect.signature(pydantic_tool.function)
    ArgsModel = sig.parameters['args'].annotation
    
    mode_field = ArgsModel.model_fields["mode"]
    assert get_args(mode_field.annotation) == ("fast", "slow")
    
    tags_field = ArgsModel.model_fields["tags"]
    assert get_args(tags_field.annotation)[0] is str
    
@pytest.mark.asyncio
async def test_base_tool_validate_params_wrapping():
    """Test that single value arguments are wrapped if schema has one property."""
    params = {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        }
    }
    tool = MockTool(name="wrap_tool", description="desc", parameters=params)
    
    assert tool.validate_params({"query": "test"}) == {"query": "test"}
    
    assert tool.validate_params("test") == {"query": "test"}

@pytest.mark.asyncio
async def test_base_tool_error_handling():
    """Test that execution errors are caught and returned as strings."""
    class ErrorTool(BaseTool):
        async def execute(self, ctx: RunContext, args: Any) -> str:
            raise RuntimeError("Something went wrong")
            
    tool = ErrorTool(name="error_tool", description="desc")
    pydantic_tool = tool.to_pydantic_ai_tool()
    
    from unittest.mock import MagicMock
    ctx = MagicMock(spec=RunContext)
    
    import inspect
    sig = inspect.signature(pydantic_tool.function)
    ArgsModel = sig.parameters['args'].annotation
    args = ArgsModel()
    
    result = await pydantic_tool.function(ctx, args)
    assert "Error executing tool 'error_tool'" in result
    assert "RuntimeError" in result
    assert "Something went wrong" in result


@pytest.mark.parametrize("provider", ["openai", "claude", "deepseek"])
def test_provider_schema_defaults(provider):
    schema = to_provider_schema(provider, None)
    assert schema["type"] == "object"
    assert schema["properties"] == {}


@pytest.mark.parametrize("provider", ["openai", "claude", "deepseek"])
def test_provider_schema_preserves_shapes(provider):
    params = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["fast", "slow"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "payload": {"type": "object", "properties": {"id": {"type": "integer"}}},
        },
        "required": ["mode"]
    }
    schema = to_provider_schema(provider, params)
    assert schema["required"] == ["mode"]
    assert schema["properties"]["mode"]["enum"] == ["fast", "slow"]
    assert schema["properties"]["tags"]["items"]["type"] == "string"
    assert schema["properties"]["payload"]["type"] == "object"


def test_exec_tool_local_mode_overrides():
    from app.mcp.builtin.exec import ExecToolConfig
    import os

    config = ExecToolConfig.from_settings({"local_mode": True})
    assert config.allow_patterns == []
    assert config.timeout_s >= 180
    assert config.restrict_to_workspace is True
    if os.name != "nt":
        assert config.enable_windows_path_checks is False


def test_exec_tool_default_denylist():
    from app.mcp.builtin.exec import ExecToolConfig

    config = ExecToolConfig.from_settings({})
    assert config.deny_patterns


def test_exec_tool_allowlist_enforced():
    from app.mcp.builtin.exec import ExecToolConfig, ExecTool
    from unittest.mock import MagicMock

    config = ExecToolConfig.from_settings({
        "allow_patterns": ["^echo\\b"]
    })
    tool = ExecTool(config)
    ctx = MagicMock()

    result = None
    try:
        import asyncio
        result = asyncio.run(tool.execute(ctx, {"command": "ls", "working_dir": "."}))
    except PermissionError as e:
        result = str(e)

    assert result and "allowlist" in result
