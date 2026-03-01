from typing import Any, Dict, Optional, Type, Callable, Awaitable
from abc import ABC, abstractmethod
from dataclasses import replace
import pydantic
import re
import logging
from pydantic_ai import Tool, RunContext
from mcp import ClientSession
from .schema_translator import to_provider_schema

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """
    Base class for all tools in the system.
    Provides a unified interface for schema generation and execution.
    """
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or {"type": "object", "properties": {}}

    @abstractmethod
    async def execute(self, ctx: RunContext, args: Any) -> str:
        """Execute the tool logic."""
        pass

    def validate_params(self, args: Any) -> Dict[str, Any]:
        """
        Validate and potentially transform arguments before execution.
        Returns a dictionary of validated arguments.
        """
        if args is None:
            return {}
        
        # If it's a Pydantic model (from pydantic-ai), convert to dict
        if hasattr(args, "model_dump"):
            # Filter out None values to allow target function defaults to work
            return {k: v for k, v in args.model_dump().items() if v is not None}
        
        if not isinstance(args, dict):
            # If the LLM sent a single value but we expect an object, 
            # try to wrap it if there's only one property in schema.
            properties = self.parameters.get("properties", {})
            if len(properties) == 1:
                prop_name = list(properties.keys())[0]
                return {prop_name: args}
            raise ValueError(f"Expected dict for tool arguments, got {type(args).__name__}")
            
        return {k: v for k, v in args.items() if v is not None}

    def build_args_model(self) -> Type[pydantic.BaseModel]:
        properties = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        
        fields = {}
        for prop_name, prop_def in properties.items():
            prop_type = self._map_json_type(prop_def)
            description = prop_def.get("description", "")
            
            if prop_name in required:
                default = ...
            else:
                default = None
            
            fields[prop_name] = (prop_type, pydantic.Field(default=default, description=description))

        sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', self.name)
        model_name = f"{sanitized_name}Args"
        
        import uuid
        model_name = f"{model_name}_{uuid.uuid4().hex[:8]}"
        
        return pydantic.create_model(model_name, **fields)

    def to_pydantic_ai_tool(self, llm_name: Optional[str] = None, provider: Optional[str] = None) -> Tool:
        """Convert this tool to a pydantic-ai Tool object."""
        tool_name = llm_name or self.name
        ArgsModel = self.build_args_model()

        async def wrapper(ctx: RunContext, args: ArgsModel) -> str:
            try:
                validated_args = self.validate_params(args)
                return await self.execute(ctx, validated_args)
            except Exception as e:
                logger.exception(f"Error executing tool '{self.name}': {str(e)}")
                error_type = type(e).__name__
                error_msg = str(e)
                return f"Error executing tool '{self.name}' ({error_type}): {error_msg}".strip()

        prepare = None
        if provider:
            async def prepare(ctx: RunContext, tool_def):
                schema = to_provider_schema(provider, self.parameters)
                return replace(tool_def, parameters_json_schema=schema)
        return Tool(wrapper, name=tool_name, description=self.description, prepare=prepare)

    def _map_json_type(self, prop_def: Any) -> Type:
        """
        Maps JSON schema type definitions to Python types.
        Supports nested objects, arrays, and enums.
        """
        from typing import List, Dict, Literal, Union
        if isinstance(prop_def, str):
            json_type = prop_def
            if json_type == "string":
                return str
            if json_type == "integer":
                return int
            if json_type == "number":
                return float
            if json_type == "boolean":
                return bool
            if json_type == "array":
                return list
            if json_type == "object":
                return dict
            return Any
        json_type = prop_def.get("type")
        
        if "enum" in prop_def:
            return Literal[tuple(prop_def["enum"])]
            
        if isinstance(json_type, list):
            types = [self._map_json_type({"type": t}) for t in json_type if t != "null"]
            if "null" in json_type:
                return Optional[Union[tuple(types)]]
            return Union[tuple(types)]

        if json_type == "string":
            return str
        elif json_type == "integer":
            return int
        elif json_type == "number":
            return float
        elif json_type == "boolean":
            return bool
        elif json_type == "array":
            items_def = prop_def.get("items")
            if items_def:
                item_type = self._map_json_type(items_def)
                return List[item_type]
            return list
        elif json_type == "object":
            return Dict[str, Any]
            
        return Any

class McpTool(BaseTool):
    """
    Tool that calls an MCP server.
    """
    def __init__(
        self,
        server_name: str,
        session: ClientSession,
        name: str,
        description: str,
        parameters: Dict[str, Any]
    ):
        super().__init__(name, description, parameters)
        self.server_name = server_name
        self.session = session

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        result = await self.session.call_tool(self.name, arguments=args)
        output = []
        for content in result.content:
            if content.type == "text":
                output.append(content.text)
            else:
                output.append(f"[{content.type}]")
        return "\n".join(output)

class BuiltinTool(BaseTool):
    """
    Tool that calls a local Python function.
    """
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Awaitable[str]]
    ):
        super().__init__(name, description, parameters)
        self.handler = handler

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self.handler(ctx, **args)
