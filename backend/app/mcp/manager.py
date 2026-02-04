from typing import List, Any, Dict, Optional, Type
import os
import json
import re
import asyncio
import logging
import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic_ai import RunContext, Tool
from pydantic import create_model, Field, BaseModel

from app.services import doc_retrieval
from app.services.config_service import config_service
from app.services.notebook_service import notebook_service
from app.services.chat_service import chat_service
from app.services.task_service import TaskSpec, task_service

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
        self._server_tasks: Dict[str, asyncio.Task] = {}
        self._server_close_events: Dict[str, asyncio.Event] = {}
        self._server_ready: Dict[str, asyncio.Future] = {}
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
            tasks = list(self._server_tasks.items())
            close_events = list(self._server_close_events.items())
            self._server_tasks.clear()
            self._server_close_events.clear()
            self._server_ready.clear()
            self.sessions.clear()

        for _name, evt in close_events:
            evt.set()

        for name, task in tasks:
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                try:
                    await task
                except Exception:
                    logger.exception("Error during MCP cleanup (cancelled): %s", name)
                continue
            except Exception:
                logger.exception("Error during MCP cleanup: %s", name)

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

    async def _handle_server_task_done(self, name: str, exc: Optional[BaseException]) -> None:
        async with self._lock:
            self._server_tasks.pop(name, None)
            self._server_close_events.pop(name, None)
            self._server_ready.pop(name, None)
            self.sessions.pop(name, None)
            if exc:
                self.last_errors[name] = str(exc)

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

            close_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            ready: asyncio.Future = loop.create_future()

            async def _run_server() -> None:
                try:
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            if not ready.done():
                                ready.set_result(session)
                            await close_event.wait()
                except Exception as e:
                    if not ready.done():
                        ready.set_exception(e)
                    raise

            task = asyncio.create_task(_run_server(), name=f"mcp_server:{name}")

            def _done_callback(t: asyncio.Task) -> None:
                exc = None
                try:
                    exc = t.exception()
                except asyncio.CancelledError as e:
                    exc = e
                asyncio.create_task(self._handle_server_task_done(name, exc))

            task.add_done_callback(_done_callback)

            self._server_tasks[name] = task
            self._server_close_events[name] = close_event
            self._server_ready[name] = ready

            session: ClientSession = await ready
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

    async def notebook_create_note(self, ctx: RunContext[Any], title: str, content: str) -> str:
        note = notebook_service.create_note(title=title, content=content)
        return json.dumps(json.loads(note.model_dump_json()), ensure_ascii=False, indent=2)

    async def notebook_list_notes(self, ctx: RunContext[Any], limit: int = 20, query: Optional[str] = None) -> str:
        notes = notebook_service.list_notes()
        if query:
            q = query.lower()
            notes = [n for n in notes if q in (n.title or "").lower() or q in (n.content or "").lower()]
        notes = notes[: max(0, int(limit))]
        payload = [
            {
                "id": n.id,
                "title": n.title,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in notes
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def notebook_read_note(self, ctx: RunContext[Any], note_id: str) -> str:
        note = notebook_service.get_note(note_id)
        if not note:
            return json.dumps({"error": "not_found", "note_id": note_id}, ensure_ascii=False, indent=2)
        return json.dumps(json.loads(note.model_dump_json()), ensure_ascii=False, indent=2)

    async def notebook_update_note(
        self,
        ctx: RunContext[Any],
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
    ) -> str:
        note = notebook_service.update_note(note_id, title=title, content=content)
        if not note:
            return json.dumps({"error": "not_found", "note_id": note_id}, ensure_ascii=False, indent=2)
        return json.dumps(json.loads(note.model_dump_json()), ensure_ascii=False, indent=2)

    async def chat_list_sessions(self, ctx: RunContext[Any], limit: int = 50, query: Optional[str] = None) -> str:
        data = chat_service.list_sessions_meta(limit=limit, query=query)
        return json.dumps(data, ensure_ascii=False, indent=2)

    async def chat_list_messages(self, ctx: RunContext[Any], chat_id: str, limit: int = 50, offset: int = 0) -> str:
        data = chat_service.list_messages_meta(chat_id=chat_id, limit=limit, offset=offset)
        return json.dumps(data, ensure_ascii=False, indent=2)

    async def chat_search_messages(
        self,
        ctx: RunContext[Any],
        query: str,
        limit: int = 20,
        chat_id: Optional[str] = None,
    ) -> str:
        data = chat_service.search_messages(query=query, limit=limit, chat_id=chat_id)
        return json.dumps(data, ensure_ascii=False, indent=2)

    async def mcp_get_status(self, ctx: RunContext[Any]) -> str:
        return json.dumps(self.get_status(), ensure_ascii=False, indent=2)

    async def mcp_list_tools(self, ctx: RunContext[Any], server: Optional[str] = None) -> str:
        tools = await self.get_available_tools()
        if server:
            tools = [t for t in tools if t.get("server") == server]
        payload = [{"id": t.get("id"), "name": t.get("name"), "server": t.get("server")} for t in tools]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def task_tool(
        self,
        ctx: RunContext[Any],
        tasks: list[TaskSpec],
        parent_chat_id: Optional[str] = None,
    ) -> str:
        deps = getattr(ctx, "deps", None)
        effective_parent = parent_chat_id
        if not effective_parent and isinstance(deps, dict):
            effective_parent = deps.get("chat_id")
        if not effective_parent:
            return json.dumps({"error": "missing_parent_chat_id"}, ensure_ascii=False, indent=2)

        q = deps.get("task_event_queue") if isinstance(deps, dict) else None
        trace_id = deps.get("trace_id") if isinstance(deps, dict) else None
        auth_scope = deps.get("auth_scope") if isinstance(deps, dict) else None
        context_refs = deps.get("context_refs") if isinstance(deps, dict) else None

        def _emit(evt):
            if q is None:
                return
            try:
                q.put_nowait(evt.model_dump(mode="json"))
            except Exception:
                return

        normalized_tasks: list[TaskSpec] = []
        for t in tasks:
            update: dict[str, Any] = {}
            if trace_id and not getattr(t, "trace_id", None):
                update["trace_id"] = trace_id
            if auth_scope is not None and getattr(t, "auth_scope", None) is None:
                update["auth_scope"] = auth_scope
            if context_refs is not None and getattr(t, "context_refs", None) is None:
                update["context_refs"] = context_refs
            normalized_tasks.append(t.model_copy(update=update) if update else t)

        result = await task_service.run_tasks(effective_parent, normalized_tasks, emit=_emit)
        if isinstance(deps, dict):
            parent_citations = deps.get("citations")
            if isinstance(parent_citations, list):
                existing = {c.get("path") for c in parent_citations if isinstance(c, dict)}
                for t in result.tasks:
                    citations = getattr(t, "citations", None)
                    if not isinstance(citations, list):
                        continue
                    for c in citations:
                        if not isinstance(c, dict):
                            continue
                        path = c.get("path")
                        if isinstance(path, str) and path in existing:
                            continue
                        parent_citations.append(c)
                        if isinstance(path, str):
                            existing.add(path)
        return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)

    def _get_builtin_tools(self) -> List[tuple[str, Any]]:
        return [
            ("docs_search_markdown", self.docs_search_markdown),
            ("docs_read_markdown", self.docs_read_markdown),
            ("get_current_time", self.get_current_time),
            ("notebook_create_note", self.notebook_create_note),
            ("notebook_list_notes", self.notebook_list_notes),
            ("notebook_read_note", self.notebook_read_note),
            ("notebook_update_note", self.notebook_update_note),
            ("chat_list_sessions", self.chat_list_sessions),
            ("chat_list_messages", self.chat_list_messages),
            ("chat_search_messages", self.chat_search_messages),
            ("mcp_get_status", self.mcp_get_status),
            ("mcp_list_tools", self.mcp_list_tools),
            ("task_tool", self.task_tool),
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
                        "root": {"type": "string", "description": "Target folder relative to project root (default: docs)."},
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
                        "root": {"type": "string", "description": "Target folder relative to project root (default: docs)."},
                        "path": {"type": "string"},
                        "start_line": {"type": "integer"},
                        "max_lines": {"type": "integer"},
                    },
                    "required": ["path"],
                },
            },
            {
                "id": "builtin:get_current_time",
                "name": "get_current_time",
                "description": "Return current server time in ISO format.",
                "server": "builtin",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "id": "builtin:notebook_create_note",
                "name": "notebook_create_note",
                "description": "Create a note in Yue Notebook.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["title", "content"],
                },
            },
            {
                "id": "builtin:notebook_list_notes",
                "name": "notebook_list_notes",
                "description": "List notes (optionally filter by query).",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}, "query": {"type": "string"}},
                },
            },
            {
                "id": "builtin:notebook_read_note",
                "name": "notebook_read_note",
                "description": "Read a note by id.",
                "server": "builtin",
                "input_schema": {"type": "object", "properties": {"note_id": {"type": "string"}}, "required": ["note_id"]},
            },
            {
                "id": "builtin:notebook_update_note",
                "name": "notebook_update_note",
                "description": "Update an existing note by id.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {"note_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["note_id"],
                },
            },
            {
                "id": "builtin:chat_list_sessions",
                "name": "chat_list_sessions",
                "description": "List chat sessions (metadata only).",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}, "query": {"type": "string"}},
                },
            },
            {
                "id": "builtin:chat_list_messages",
                "name": "chat_list_messages",
                "description": "List messages in a chat session with pagination.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {"chat_id": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}},
                    "required": ["chat_id"],
                },
            },
            {
                "id": "builtin:chat_search_messages",
                "name": "chat_search_messages",
                "description": "Search messages by keyword (returns snippets).",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}, "chat_id": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "id": "builtin:mcp_get_status",
                "name": "mcp_get_status",
                "description": "Get MCP status (enabled/connected/last_error).",
                "server": "builtin",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "id": "builtin:mcp_list_tools",
                "name": "mcp_list_tools",
                "description": "List available tools (optionally filter by server).",
                "server": "builtin",
                "input_schema": {"type": "object", "properties": {"server": {"type": "string"}}},
            },
            {
                "id": "builtin:task_tool",
                "name": "task_tool",
                "description": "Run sub tasks by delegating to child agents and stream progress via SSE.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "parent_chat_id": {"type": "string"},
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "prompt": {"type": "string"},
                                    "agent_id": {"type": "string"},
                                    "system_prompt": {"type": "string"},
                                    "provider": {"type": "string"},
                                    "model": {"type": "string"},
                                    "trace_id": {"type": "string"},
                                    "deadline_ts": {"type": "number"},
                                    "auth_scope": {"type": "object"},
                                    "context_refs": {"type": "array"},
                                },
                                "required": ["prompt"],
                            },
                        },
                    },
                    "required": ["tasks"],
                },
            },
        ]

    def _get_allow_roots(self) -> List[str]:
        doc_access = config_service.get_doc_access()
        allow_roots = doc_access.get("allow_roots") if isinstance(doc_access, dict) else []
        return [r for r in allow_roots if isinstance(r, str) and r.strip()]

    def _get_deny_roots(self) -> List[str]:
        doc_access = config_service.get_doc_access()
        deny_roots = doc_access.get("deny_roots") if isinstance(doc_access, dict) else []
        return [r for r in deny_roots if isinstance(r, str) and r.strip()]

    async def docs_search_markdown(self, ctx: RunContext[Any], query: str, limit: int = 5, root: Optional[str] = None) -> str:
        deps = getattr(ctx, "deps", None)
        effective_root = root
        if not effective_root and isinstance(deps, dict):
            effective_root = deps.get("doc_root")
        docs_root = doc_retrieval.resolve_target_root(
            effective_root or "docs",
            allow_roots=self._get_allow_roots(),
            deny_roots=self._get_deny_roots(),
        )
        hits = doc_retrieval.search_markdown(query, limit=limit, docs_root=docs_root)
        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                existing = {c.get("path") for c in citations if isinstance(c, dict)}
                for h in hits:
                    if h.path in existing:
                        continue
                    citations.append(
                        {"path": h.path, "snippet": h.snippet, "score": h.score, "locator": h.locator, "reason": h.reason}
                    )
                    existing.add(h.path)
        payload = [{"path": h.path, "snippet": h.snippet, "score": h.score, "locator": h.locator, "reason": h.reason} for h in hits]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def docs_read_markdown(
        self,
        ctx: RunContext[Any],
        path: str,
        start_line: int = 1,
        max_lines: int = 200,
        root: Optional[str] = None,
    ) -> str:
        deps = getattr(ctx, "deps", None)
        effective_root = root
        if not effective_root and isinstance(deps, dict):
            effective_root = deps.get("doc_root")
        docs_root = doc_retrieval.resolve_target_root(
            effective_root or "docs",
            allow_roots=self._get_allow_roots(),
            deny_roots=self._get_deny_roots(),
        )
        abs_path, start, end, snippet = doc_retrieval.read_markdown_lines(
            path,
            docs_root=docs_root,
            start_line=start_line,
            max_lines=max_lines,
        )
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
