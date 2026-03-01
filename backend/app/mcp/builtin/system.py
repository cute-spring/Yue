import datetime
from typing import Any, Dict
from pydantic_ai import RunContext
from ..base import BaseTool
from .registry import builtin_tool_registry

class GetCurrentTimeTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="get_current_time",
            description="Returns the current server time in ISO format.",
            parameters={"type": "object", "properties": {}}
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return datetime.datetime.now().isoformat()

# Register the tool
builtin_tool_registry.register(GetCurrentTimeTool())
