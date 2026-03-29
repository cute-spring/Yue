import pytest
from app.mcp.builtin.registry import BuiltinToolRegistry
from app.mcp.base import BaseTool
from pydantic_ai import RunContext

class MockTool(BaseTool):
    def __init__(self, name="mock_tool"):
        super().__init__(name, "Mock tool description", {"type": "object", "properties": {}})

    async def execute(self, ctx: RunContext, args: dict) -> str:
        return "mock result"

def test_registry_register_and_get():
    registry = BuiltinToolRegistry()
    tool = MockTool()
    registry.register(tool)
    
    assert registry.get_tool("mock_tool") == tool
    assert len(registry.get_all_tools()) == 1

def test_registry_metadata():
    registry = BuiltinToolRegistry()
    registry.register(MockTool("tool_a"))
    registry.register(MockTool("tool_b"))
    
    metadata = registry.get_all_metadata()
    assert len(metadata) == 2
    assert metadata[0]["id"] == "builtin:tool_a"
    assert metadata[0]["server"] == "builtin"
    assert metadata[0]["input_schema"] == {"type": "object", "properties": {}}
    assert metadata[1]["id"] == "builtin:tool_b"
