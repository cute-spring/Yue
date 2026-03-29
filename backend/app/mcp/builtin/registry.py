from typing import Dict, List, Any, Optional
import logging
from ..base import BaseTool

logger = logging.getLogger(__name__)

class BuiltinToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a new built-in tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' is already registered and will be overwritten.")
        self._tools[tool.name] = tool
        logger.debug(f"Registered built-in tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return [self._tools[name] for name in sorted(self._tools.keys())]

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all registered tools in the format expected by the frontend."""
        metadata = []
        for tool in self.get_all_tools():
            payload = {
                "id": f"builtin:{tool.name}",
                "name": tool.name,
                "description": tool.description,
                "server": "builtin",
                "input_schema": tool.parameters,
            }
            output_schema = getattr(tool, "output_schema", None)
            if isinstance(output_schema, dict):
                payload["output_schema"] = output_schema
            contract_metadata = getattr(tool, "contract_metadata", None)
            if isinstance(contract_metadata, dict):
                payload["metadata"] = contract_metadata
            metadata.append(payload)
        return sorted(metadata, key=lambda x: x["name"])

# Global instance for easy access
builtin_tool_registry = BuiltinToolRegistry()
