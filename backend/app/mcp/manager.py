from typing import List, Any, Dict, Optional, Type
import os
import json
import re
import asyncio
import logging
from contextlib import AsyncExitStack
import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic_ai import RunContext, Tool
from pydantic import create_model, Field, BaseModel

from app.services import doc_retrieval

logger = logging.getLogger(__name__)

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
        self._lock = asyncio.Lock()
        self.sessions: Dict[str, ClientSession] = {}
        self.last_errors: Dict[str, str] = {}
        self.initialized = True

    async def initialize(self):
        """Connect to all configured servers."""
        async with self._lock:
            configs = self.load_config()
            logger.info("Loading MCP configs from %s: %s", self.config_path, configs)
            for config in configs:
                try:
                    if config.get("enabled", True):
                        await self._connect_to_server_unlocked(config)
                except Exception as e:
                    logger.exception("Failed to connect to %s", config.get("name"))
                    name = config.get("name") or "unknown"
                    self.last_errors[name] = str(e)

    async def cleanup(self):
        """Close all connections."""
        async with self._lock:
            try:
                await self.exit_stack.aclose()
            except Exception:
                logger.exception("Error during MCP cleanup")
            self.exit_stack = AsyncExitStack()
            self.sessions.clear()

    def load_config(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.config_path):
            return []
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.exception("Error loading MCP config")
            return []

    async def connect_to_server(self, config: Dict[str, Any]):
        async with self._lock:
            return await self._connect_to_server_unlocked(config)

    async def _connect_to_server_unlocked(self, config: Dict[str, Any]):
        name = config.get("name")
        if not name:
            return
            
        if name in self.sessions:
            return self.sessions[name]

        transport = config.get("transport", "stdio")
        logger.info("Connecting to MCP server: %s (%s)", name, transport)
        
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
            logger.info("Connected to %s", name)
            return session
        
        # TODO: Implement SSE
        return None

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all available tools from connected servers.
        Used for UI configuration.
        """
        async with self._lock:
            tools = []
            for name, session in self.sessions.items():
                try:
                    if getattr(session, "is_closed", False):
                        continue
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
                    logger.exception("Error listing tools for %s", name)
            tools.extend(self._get_builtin_tools_metadata())
            return sorted(tools, key=lambda t: (t.get("server", ""), t.get("name", "")))

    async def get_tools_for_agent(self, agent_id: Optional[str]) -> List[Any]:
        """
        Dynamically connects to MCP servers authorized for the agent
        and returns tools compatible with Pydantic AI.
        """
        async with self._lock:
            tools = []

            from app.services.agent_store import agent_store
            agent = agent_store.get_agent(agent_id) if agent_id else None

            allowed_tools = None
            if agent:
                allowed_tools = set(agent.enabled_tools)

            # In a real app, we would filter by agent_id
            # For now, expose all tools from all connected sessions
            for name, session in self.sessions.items():
                try:
                    if getattr(session, "is_closed", False):
                        continue
                    result = await session.list_tools()
                    for tool in result.tools:
                        composite_id = f"{name}:{tool.name}"
                        if allowed_tools is not None and (composite_id not in allowed_tools and tool.name not in allowed_tools):
                            continue
                        tools.append(self._convert_tool(name, session, tool))
                except Exception as e:
                    logger.exception("Error listing tools for %s", name)

            for tool_name, tool_func in self._get_builtin_tools():
                composite_id = f"builtin:{tool_name}"
                if allowed_tools is not None and (composite_id not in allowed_tools and tool_name not in allowed_tools):
                    continue
                tools.append(tool_func)

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

    def _get_builtin_tools(self) -> List[tuple[str, Any]]:
        return [
            ("docs_search_markdown", self.docs_search_markdown),
            ("docs_read_markdown", self.docs_read_markdown),
            ("get_current_time", self.get_current_time),
        ]

    def _get_builtin_tools_metadata(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "builtin:docs_search_markdown",
                "name": "docs_search_markdown",
                "description": "Search Markdown files under Yue/docs and return matching snippets.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "id": "builtin:docs_read_markdown",
                "name": "docs_read_markdown",
                "description": "Read a Markdown file under Yue/docs with line-based pagination.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start_line": {"type": "integer"},
                        "max_lines": {"type": "integer"},
                    },
                    "required": ["path"],
                },
            },
        ]

    async def docs_search_markdown(self, ctx: RunContext[Any], query: str, limit: int = 5) -> str:
        hits = doc_retrieval.search_markdown(query, limit=limit)
        deps = getattr(ctx, "deps", None)
        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                existing = {c.get("path") for c in citations if isinstance(c, dict)}
                for h in hits:
                    if h.path in existing:
                        continue
                    citations.append({"path": h.path, "snippet": h.snippet, "score": h.score})
                    existing.add(h.path)
        payload = [{"path": h.path, "snippet": h.snippet, "score": h.score} for h in hits]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def docs_read_markdown(
        self,
        ctx: RunContext[Any],
        path: str,
        start_line: int = 1,
        max_lines: int = 200,
    ) -> str:
        abs_path, start, end, snippet = doc_retrieval.read_markdown_lines(
            path,
            start_line=start_line,
            max_lines=max_lines,
        )
        deps = getattr(ctx, "deps", None)
        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                citations.append(
                    {
                        "path": abs_path,
                        "start_line": start,
                        "end_line": end,
                        "snippet": snippet,
                    }
                )
        return f"{abs_path}#L{start}-L{end}\n{snippet}"

# Global instance
mcp_manager = McpManager()
