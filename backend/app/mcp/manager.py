from typing import List, Any, Dict, Optional, Type
import os
import json
import re
import asyncio
from contextlib import AsyncExitStack
import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic_ai import RunContext, Tool
from pydantic import create_model, Field, BaseModel

class McpManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(McpManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.config_path = os.path.join(os.path.dirname(__file__), "../../data/mcp_configs.json")
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}
        self.last_errors: Dict[str, str] = {}
        self.initialized = True

    async def initialize(self):
        """Connect to all configured servers."""
        configs = self.load_config()
        print(f"Loading MCP configs from {self.config_path}: {configs}")
        for config in configs:
            try:
                if config.get("enabled", True):
                    await self.connect_to_server(config)
            except Exception as e:
                print(f"Failed to connect to {config.get('name')}: {e}")
                name = config.get("name") or "unknown"
                self.last_errors[name] = str(e)

    async def cleanup(self):
        """Close all connections."""
        await self.exit_stack.aclose()
        self.sessions.clear()

    def load_config(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.config_path):
            return []
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading MCP config: {e}")
            return []

    async def connect_to_server(self, config: Dict[str, Any]):
        name = config.get("name")
        if not name:
            return
            
        if name in self.sessions:
            return self.sessions[name]

        transport = config.get("transport", "stdio")
        print(f"Connecting to MCP server: {name} ({transport})")
        
        if transport == "stdio":
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env", None)
            
            # Resolve placeholders in args
            # In a self-contained structure, PROJECT_ROOT is the parent of the backend directory (the 'Yue' folder)
            # manager.py is in Yue/backend/app/mcp/, so ../../../ is Yue/
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            
            resolved_args = []
            for arg in args:
                if isinstance(arg, str):
                    resolved_arg = arg.replace("${PROJECT_ROOT}", project_root)
                    resolved_args.append(resolved_arg)
                else:
                    resolved_args.append(arg)
            
            server_params = StdioServerParameters(
                command=command,
                args=resolved_args,
                env={**os.environ, **(env or {})}
            )
            
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.sessions[name] = session
            print(f"Connected to {name}")
            return session
        
        # TODO: Implement SSE
        return None

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all available tools from connected servers.
        Used for UI configuration.
        """
        tools = []
        for name, session in self.sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    tools.append({
                        "id": f"{name}:{tool.name}",
                        "name": tool.name,
                        "description": tool.description,
                        "server": name,
                        "input_schema": tool.inputSchema
                    })
            except Exception as e:
                print(f"Error listing tools for {name}: {e}")
        return tools

    async def get_tools_for_agent(self, agent_id: str) -> List[Any]:
        """
        Dynamically connects to MCP servers authorized for the agent
        and returns tools compatible with Pydantic AI.
        """
        tools = []
        
        from app.services.agent_store import agent_store
        agent = agent_store.get_agent(agent_id)
        
        allowed_tools = None
        if agent:
            allowed_tools = set(agent.enabled_tools)
        
        # In a real app, we would filter by agent_id
        # For now, expose all tools from all connected sessions
        for name, session in self.sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    composite_id = f"{name}:{tool.name}"
                    if allowed_tools is not None and (composite_id not in allowed_tools and tool.name not in allowed_tools):
                        continue
                    tools.append(self._convert_tool(name, session, tool))
            except Exception as e:
                print(f"Error listing tools for {name}: {e}")
        
        # Add a built-in demo tool
        tools.append(self.get_current_time)
        
        return tools

    def get_status(self) -> List[Dict[str, Any]]:
        """
        Returns per-server status derived from config and active sessions.
        """
        configs = self.load_config()
        status_list = []
        for cfg in configs:
            name = cfg.get("name")
            enabled = cfg.get("enabled", True)
            connected = name in self.sessions
            status_list.append({
                "name": name,
                "enabled": enabled,
                "connected": connected,
                "transport": cfg.get("transport", "stdio"),
                "last_error": self.last_errors.get(name)
            })
        return status_list

    def _convert_tool(self, server_name: str, session: ClientSession, tool_def: Any) -> Tool:
        
        # Create Pydantic model for arguments
        input_schema = tool_def.inputSchema
        
        fields = {}
        if "properties" in input_schema:
            for prop_name, prop_def in input_schema["properties"].items():
                prop_type = self._map_json_type(prop_def.get("type", "string"))
                description = prop_def.get("description", None)
                
                is_required = prop_name in input_schema.get("required", [])
                if is_required:
                    default = ...
                else:
                    default = None
                
                fields[prop_name] = (prop_type, Field(default=default, description=description))
        
        # If no properties, make an empty model
        if not fields:
             ArgsModel = create_model(f"{tool_def.name}Args")
        else:
             ArgsModel = create_model(f"{tool_def.name}Args", **fields)

        async def wrapper(ctx: RunContext, args: ArgsModel) -> str:
            # call_tool expects arguments as dict
            result = await session.call_tool(tool_def.name, arguments=args.model_dump())
            # Result content is a list of TextContent or ImageContent or EmbeddedResource
            # We assume text for now and join them
            output = []
            for content in result.content:
                if content.type == "text":
                    output.append(content.text)
                else:
                    output.append(f"[{content.type}]")
            return "\n".join(output)
        
        # Pydantic AI Tool
        # Sanitize tool name for LLM compatibility (regex: ^[a-zA-Z0-9_-]+$)
        # We also prefix with server name to avoid collisions
        sanitized_server = re.sub(r'[^a-zA-Z0-9_-]', '_', server_name)
        sanitized_tool = re.sub(r'[^a-zA-Z0-9_-]', '_', tool_def.name)
        llm_tool_name = f"mcp__{sanitized_server}__{sanitized_tool}"
        
        return Tool(wrapper, name=llm_tool_name, description=tool_def.description)

    def _map_json_type(self, json_type: str) -> Type:
        if json_type == "string":
            return str
        elif json_type == "integer":
            return int
        elif json_type == "number":
            return float
        elif json_type == "boolean":
            return bool
        elif json_type == "array":
            return list
        elif json_type == "object":
            return dict
        return Any

    # Demo tool
    def get_current_time(self, ctx: RunContext[Any]) -> str:
        """Returns the current time."""
        return datetime.datetime.now().isoformat()

# Global instance
mcp_manager = McpManager()
