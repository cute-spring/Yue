from typing import List, Any, Dict, Optional, Type
import os
import sys
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
from app.services.config_service import config_service

import shutil
from .models import ServerConfig
from .base import McpTool, BuiltinTool

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
        self.server_info: Dict[str, Dict[str, Any]] = {} # Store server name and version
        self.is_initializing = False
        self.initialized = True

    async def initialize(self):
        """Connect to all configured servers."""
        async with self._lock:
            if self.is_initializing:
                logger.info("MCP initialization already in progress.")
                return
            self.is_initializing = True
            
        try:
            configs = self.load_config()
            logger.info("Loading MCP configs from %s: %s", self.config_path, self._redact_configs(configs))
            
            # Use asyncio.gather to connect to all servers in parallel
            tasks = []
            for config in configs:
                try:
                    # Validate config structure
                    validated_config = ServerConfig(**config).model_dump()
                    if validated_config.get("enabled", True):
                        tasks.append(self._connect_with_retry_and_timeout(validated_config))
                except Exception as e:
                    name = config.get("name") or "unknown"
                    logger.error("Invalid config for MCP server %s: %s", name, str(e))
                    self.last_errors[name] = f"Invalid configuration: {str(e)}"
            
            if tasks:
                # Release the lock while waiting for all connections
                await asyncio.gather(*tasks)
        finally:
            async with self._lock:
                self.is_initializing = False

    async def _connect_with_retry_and_timeout(self, config: Dict[str, Any]):
        name = config.get("name") or "unknown"
        max_retries = 2 # Increased retry
        timeout = config.get("timeout", 60.0)
        
        # Check if command exists before attempting to connect
        command = config.get("command")
        if command and not shutil.which(command):
            # Try to resolve relative to project root if it's not in PATH
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            local_cmd = os.path.join(project_root, command)
            if not os.path.exists(local_cmd):
                logger.error("Command not found for MCP server %s: %s", name, command)
                self.last_errors[name] = f"Command not found: {command}"
                return

        for attempt in range(max_retries + 1):
            try:
                await asyncio.wait_for(self._connect_to_server_unlocked(config), timeout=timeout)
                return
            except asyncio.TimeoutError:
                logger.error("Timeout connecting to MCP server: %s (attempt %d/%d)", name, attempt + 1, max_retries + 1)
                self.last_errors[name] = "Connection timeout"
            except Exception as e:
                logger.exception("Failed to connect to %s (attempt %d/%d)", name, attempt + 1, max_retries + 1)
                self.last_errors[name] = str(e)
            
            if attempt < max_retries:
                # Exponential backoff for retries
                await asyncio.sleep(min(2 ** attempt, 10))

    async def cleanup(self):
        """Close all connections."""
        async with self._lock:
            try:
                await self.exit_stack.aclose()
            except Exception:
                logger.exception("Error during MCP cleanup")
            self.exit_stack = AsyncExitStack()
            self.sessions.clear()
            self.server_info.clear()

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
            
        existing = self.sessions.get(name)
        if existing and not getattr(existing, "is_closed", False):
            return existing
        if existing and getattr(existing, "is_closed", False):
            self.sessions.pop(name, None)
            self.server_info.pop(name, None)

        transport = config.get("transport", "stdio")
        logger.info("Connecting to MCP server: %s (%s)", name, transport)
        
        if transport == "stdio":
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env", None)
            
            # Resolve placeholders in args
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            
            resolved_args = []
            for arg in args:
                if isinstance(arg, str):
                    resolved_arg = arg.replace("${PROJECT_ROOT}", project_root)
                    resolved_args.append(resolved_arg)
                else:
                    resolved_args.append(arg)
            
            # Add proxy settings to MCP server environment if configured
            llm_config = config_service.get_llm_config()
            proxy_url = llm_config.get('proxy_url')
            from app.services.llm.utils import get_ssl_verify, _build_no_proxy_value
            ssl_verify = get_ssl_verify()
            
            mcp_env = {**os.environ, **(env or {})}
            if proxy_url:
                for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
                    mcp_env[key] = proxy_url
                
                no_proxy_val = _build_no_proxy_value(llm_config.get('no_proxy'), llm_config)
                mcp_env["NO_PROXY"] = no_proxy_val
                mcp_env["no_proxy"] = no_proxy_val
                
            if isinstance(ssl_verify, str):
                mcp_env["SSL_CERT_FILE"] = ssl_verify

            server_params = StdioServerParameters(
                command=command,
                args=resolved_args,
                env=mcp_env
            )
            
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            init_result = await session.initialize()
            
            # Extract server version and info if available
            server_v = "unknown"
            if hasattr(init_result, "serverInfo"):
                server_v = getattr(init_result.serverInfo, "version", "unknown")
                self.server_info[name] = {
                    "name": getattr(init_result.serverInfo, "name", "unknown"),
                    "version": server_v
                }
            
            # Version compatibility check
            min_v = config.get("min_version")
            if min_v and server_v != "unknown":
                if not self._is_version_compatible(server_v, min_v):
                    error_msg = f"Incompatible version: {server_v} < {min_v}"
                    logger.error("MCP server %s version error: %s", name, error_msg)
                    self.last_errors[name] = error_msg
                    # Optionally disconnect or just keep as warning
            
            self.sessions[name] = session
            self.last_errors.pop(name, None) # Clear error on success
            logger.info("Connected to %s (version: %s)", name, server_v)
            return session
        
        # TODO: Implement SSE
        return None

    def _is_version_compatible(self, current: str, required: str) -> bool:
        """Simple semantic version comparison."""
        try:
            c_parts = [int(p) for p in re.split(r'[^0-9]', current) if p.isdigit()]
            r_parts = [int(p) for p in re.split(r'[^0-9]', required) if p.isdigit()]
            
            for i in range(max(len(c_parts), len(r_parts))):
                c = c_parts[i] if i < len(c_parts) else 0
                r = r_parts[i] if i < len(r_parts) else 0
                if c > r: return True
                if c < r: return False
            return True
        except Exception:
            return True # Fallback if parsing fails

    def _redact_configs(self, configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        redacted = []
        for cfg in configs:
            item = dict(cfg)
            env = item.get("env")
            if isinstance(env, dict):
                masked_env = {}
                for k, v in env.items():
                    key = str(k).lower()
                    if any(token in key for token in ("key", "secret", "token", "password")):
                        masked_env[k] = "****"
                    else:
                        masked_env[k] = v
                item["env"] = masked_env
            redacted.append(item)
        return redacted

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
            info = self.server_info.get(name, {})
            status_list.append({
                "name": name,
                "enabled": enabled,
                "connected": connected,
                "transport": cfg.get("transport", "stdio"),
                "last_error": self.last_errors.get(name),
                "server_name": info.get("name"),
                "version": info.get("version")
            })
        return status_list


    # Demo tool
    def get_current_time(self, ctx: RunContext[Any]) -> str:
        """Returns the current time."""
        return datetime.datetime.now().isoformat()

    async def generate_pptx(self, ctx: RunContext[Any], data: dict) -> str:
        """
        Generate a PowerPoint (.pptx) file from a structured JSON object.
        
        Args:
            data: A dictionary containing:
                - title (str): The main title of the PPT.
                - subtitle (str): The subtitle.
                - slides (list): A list of slide objects, each with:
                    - title (str): Slide title.
                    - content (list of str): Bullet points (max 6).
                    - layout (str, optional): Layout type (e.g., 'title_and_content').
                - output_file (str, optional): Desired filename.
        """
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        project_root = os.path.abspath(os.path.join(backend_dir, "../"))
        script_path = os.path.join(project_root, ".trae/skills/ppt-expert/scripts/generate_pptx.py")
        exports_dir = os.path.join(backend_dir, "data/exports")
        
        if not os.path.exists(script_path):
            return f"Error: PPT generation script not found at {script_path}"

        # Ensure exports directory exists
        os.makedirs(exports_dir, exist_ok=True)

        # Generate a unique filename if not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = data.get("output_file") or f"presentation_{timestamp}.pptx"
        if not filename.endswith(".pptx"):
            filename += ".pptx"
        
        # Ensure it's just the filename, not a path
        filename = os.path.basename(filename)
        output_path = os.path.join(exports_dir, filename)
        
        # Update data with the absolute path for the script to write to
        data["output_file"] = output_path

        try:
            # Run the script with JSON input
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=json.dumps(data).encode())
            
            if process.returncode != 0:
                return f"Error generating PPT: {stderr.decode()}"
            
            # Return both the local path and the download URL
            download_url = f"/exports/{filename}"
            return (
                f"Successfully generated PPT!\n"
                f"- **Local Path**: `{output_path}`\n"
                f"- **Download Link**: [{filename}]({download_url})\n\n"
                f"You can click the link above to download the file, or find it in the `backend/data/exports` directory."
            )
        except Exception as e:
            logger.exception("Failed to run PPT generation script")
            return f"Error: {str(e)}"

    def _get_builtin_tools(self) -> List[tuple[str, Any]]:
        return [
            ("docs_list", self.docs_list),
            ("docs_search", self.docs_search),
            ("docs_read", self.docs_read),
            ("docs_inspect", self.docs_inspect),
            ("docs_search_pdf", self.docs_search_pdf),
            ("docs_read_pdf", self.docs_read_pdf),
            ("generate_pptx", self.generate_pptx),
            ("get_current_time", self.get_current_time),
        ]

    def _get_builtin_tools_metadata(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "builtin:docs_list",
                "name": "docs_list",
                "description": "List files and directories under Yue/docs (or root_dir). Returns a tree-like listing with paths relative to the docs root.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "root_dir": {"type": "string"},
                        "max_items": {"type": "integer"},
                        "max_depth": {"type": "integer"},
                        "include_dirs": {"type": "boolean"},
                    },
                },
            },
            {
                "id": "builtin:docs_search",
                "name": "docs_search",
                "description": "Fast keyword search under Yue/docs (or root_dir) using Ripgrep. Returns smart snippets with line numbers. Use concise keywords (2-3 words) for best performance. mode=markdown/text.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "mode": {"type": "string"},
                        "root_dir": {"type": "string"},
                        "limit": {"type": "integer", "description": "Maximum number of files to return."},
                        "max_files": {"type": "integer"},
                        "timeout_s": {"type": "number"},
                    },
                    "required": ["query"],
                },
            },
            {
                "id": "builtin:docs_read",
                "name": "docs_read",
                "description": "Read file content. Only use this if `docs_search` snippets are insufficient. Supports pagination or centering via `target_line`.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "mode": {"type": "string"},
                        "root_dir": {"type": "string"},
                        "start_line": {"type": "integer"},
                        "max_lines": {"type": "integer", "description": "Maximum lines to read (default 200)."},
                        "target_line": {"type": "integer", "description": "If provided, centers the output window around this line."},
                    },
                    "required": ["path"],
                },
            },
            {
                "id": "builtin:docs_inspect",
                "name": "docs_inspect",
                "description": "Get document structure (headers), size, and metadata without reading full content. Useful for mapping large documents.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "root_dir": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
            {
                "id": "builtin:docs_search_pdf",
                "name": "docs_search_pdf",
                "description": "Search PDF files under Yue/docs (or an allowed root_dir) and return matching snippets with page locator when available.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "root_dir": {"type": "string"},
                        "limit": {"type": "integer"},
                        "max_files": {"type": "integer"},
                        "timeout_s": {"type": "number"},
                        "max_pages_per_file": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "id": "builtin:docs_read_pdf",
                "name": "docs_read_pdf",
                "description": "Read a PDF file under Yue/docs (or an allowed root_dir) with page-based pagination.",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "root_dir": {"type": "string"},
                        "start_page": {"type": "integer"},
                        "max_pages": {"type": "integer"},
                        "timeout_s": {"type": "number"},
                    },
                    "required": ["path"],
                },
            },
            {
                "id": "builtin:generate_pptx",
                "name": "generate_pptx",
                "description": "Generate a .pptx file from a structured JSON object. Use this ONLY after the user has confirmed the slide content and outline. The JSON must contain 'title', 'subtitle', and a 'slides' list (each with 'title' and 'content' array).",
                "server": "builtin",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "The presentation data including slides, titles, and layout information."
                        }
                    },
                    "required": ["data"],
                },
            },
        ]

    async def docs_search(
        self,
        ctx: RunContext[Any],
        query: str,
        mode: str = "text",
        root_dir: Optional[str] = None,
        limit: int = 5,
        max_files: int = 5000,
        timeout_s: Optional[float] = 2.0,
    ) -> str:
        # Robustly handle possible None from Pydantic wrappers
        if timeout_s is None:
            timeout_s = 2.0
        
        normalized_mode = (mode or "text").strip().lower()
        if normalized_mode == "markdown":
            allowed_extensions = [".md"]
        else:
            allowed_extensions = doc_retrieval.TEXT_LIKE_EXTENSIONS

        allow_roots, deny_roots = self._get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        roots = doc_retrieval.resolve_docs_roots_for_search(
            root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )

        merged = {}
        for docs_root in roots:
            hits = doc_retrieval.search_text(
                query,
                docs_root=docs_root,
                allowed_extensions=allowed_extensions,
                file_patterns=file_patterns if isinstance(file_patterns, list) else None,
                limit=limit,
                max_files=max_files,
                timeout_s=timeout_s,
            )
            for h in hits:
                existing = merged.get(h.path)
                if not existing or h.score > existing.score:
                    merged[h.path] = h
        hits = sorted(merged.values(), key=lambda h: (-h.score, h.path))[: max(0, limit)]

        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                existing = {c.get("path") for c in citations if isinstance(c, dict)}
                for h in hits:
                    if h.path in existing:
                        continue
                    entry = {"path": h.path, "snippet": h.snippet, "score": h.score}
                    if getattr(h, "start_line", None) is not None:
                        entry["start_line"] = h.start_line
                    if getattr(h, "end_line", None) is not None:
                        entry["end_line"] = h.end_line
                    citations.append(entry)
                    existing.add(h.path)

        payload = []
        for h in hits:
            item = {"path": h.path, "snippet": h.snippet, "score": h.score}
            if getattr(h, "start_line", None) is not None:
                item["start_line"] = h.start_line
            if getattr(h, "end_line", None) is not None:
                item["end_line"] = h.end_line
            payload.append(item)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def docs_list(
        self,
        ctx: RunContext[Any],
        root_dir: Optional[str] = None,
        max_items: int = 2000,
        max_depth: int = 6,
        include_dirs: bool = True,
    ) -> str:
        allow_roots, deny_roots = self._get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        roots = doc_retrieval.resolve_docs_roots_for_search(
            root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )
        remaining = max(0, max_items)
        payload = []
        for docs_root in roots:
            if remaining <= 0:
                break
            items = doc_retrieval.list_docs_tree(
                docs_root=docs_root,
                file_patterns=file_patterns if isinstance(file_patterns, list) else None,
                max_items=remaining,
                max_depth=max_depth,
                include_dirs=include_dirs,
            )
            payload.append({"root": docs_root, "items": items})
            remaining -= len(items)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def docs_search_pdf(
        self,
        ctx: RunContext[Any],
        query: str,
        root_dir: Optional[str] = None,
        limit: int = 5,
        max_files: int = 2000,
        timeout_s: Optional[float] = 6.0,
        max_pages_per_file: int = 6,
    ) -> str:
        # Robustly handle possible None from Pydantic wrappers
        if timeout_s is None:
            timeout_s = 6.0
            
        allow_roots, deny_roots = self._get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        roots = doc_retrieval.resolve_docs_roots_for_search(
            root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )

        merged = {}
        for docs_root in roots:
            hits = doc_retrieval.search_pdf(
                query,
                docs_root=docs_root,
                file_patterns=file_patterns if isinstance(file_patterns, list) else None,
                limit=limit,
                max_files=max_files,
                timeout_s=timeout_s,
                max_pages_per_file=max_pages_per_file,
            )
            for h in hits:
                existing = merged.get(h.path)
                if not existing or h.score > existing.score:
                    merged[h.path] = h
        hits = sorted(merged.values(), key=lambda h: (-h.score, h.path))[: max(0, limit)]

        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                existing = {c.get("path") for c in citations if isinstance(c, dict)}
                for h in hits:
                    if h.path in existing:
                        continue
                    entry = {"path": h.path, "snippet": h.snippet, "score": h.score}
                    if getattr(h, "start_page", None) is not None:
                        entry["start_page"] = h.start_page
                    if getattr(h, "end_page", None) is not None:
                        entry["end_page"] = h.end_page
                    citations.append(entry)
                    existing.add(h.path)

        payload = []
        for h in hits:
            item = {"path": h.path, "snippet": h.snippet, "score": h.score}
            if getattr(h, "start_page", None) is not None:
                item["start_page"] = h.start_page
            if getattr(h, "end_page", None) is not None:
                item["end_page"] = h.end_page
            payload.append(item)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def docs_read_pdf(
        self,
        ctx: RunContext[Any],
        path: str,
        root_dir: Optional[str] = None,
        start_page: Optional[int] = None,
        max_pages: int = 6,
        timeout_s: Optional[float] = 3.0,
    ) -> str:
        # Robustly handle possible None from Pydantic wrappers
        if timeout_s is None:
            timeout_s = 3.0
            
        allow_roots, deny_roots = self._get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=doc_retrieval.PDF_EXTENSIONS,
            require_md=False,
        )
        abs_path, start, end, snippet = doc_retrieval.read_pdf_pages(
            path,
            docs_root=docs_root,
            file_patterns=file_patterns if isinstance(file_patterns, list) else None,
            start_page=start_page,
            max_pages=max_pages,
            timeout_s=timeout_s,
        )
        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                citations.append(
                    {
                        "path": abs_path,
                        "start_page": start,
                        "end_page": end,
                        "snippet": snippet,
                    }
                )
        return f"{abs_path}#P{start}-P{end}\n{snippet}"

    async def docs_read(
        self,
        ctx: RunContext[Any],
        path: str,
        mode: str = "text",
        root_dir: Optional[str] = None,
        start_line: Optional[int] = None,
        max_lines: int = 200,
        target_line: Optional[int] = None,
    ) -> str:
        normalized_mode = (mode or "text").strip().lower()
        if normalized_mode == "markdown":
            # Fallback: if path is NOT .md, allow other text-like extensions
            if path and not path.lower().endswith(".md"):
                allowed_extensions = doc_retrieval.TEXT_LIKE_EXTENSIONS
            else:
                allowed_extensions = [".md"]
        else:
            allowed_extensions = doc_retrieval.TEXT_LIKE_EXTENSIONS

        allow_roots, deny_roots = self._get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None

        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=allowed_extensions,
            require_md=False,
        )
        abs_path, start, end, snippet = doc_retrieval.read_text_lines(
            path,
            docs_root=docs_root,
            allowed_extensions=allowed_extensions,
            file_patterns=file_patterns if isinstance(file_patterns, list) else None,
            start_line=start_line,
            max_lines=max_lines,
            target_line=target_line,
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

    async def docs_inspect(
        self,
        ctx: RunContext[Any],
        path: str,
        root_dir: Optional[str] = None,
    ) -> str:
        allow_roots, deny_roots = self._get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        
        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=doc_retrieval.TEXT_LIKE_EXTENSIONS,
            require_md=False,
        )
        
        info = doc_retrieval.inspect_doc(
            path,
            docs_root=docs_root,
            allowed_extensions=doc_retrieval.TEXT_LIKE_EXTENSIONS,
        )
        return json.dumps(info, ensure_ascii=False, indent=2)

    def _get_doc_access(self) -> tuple[List[str], List[str]]:
        cfg = config_service.get_config().get("doc_access", {})
        allow_roots = cfg.get("allow_roots") if isinstance(cfg, dict) else None
        deny_roots = cfg.get("deny_roots") if isinstance(cfg, dict) else None
        return allow_roots or [], deny_roots or []

# Global instance
mcp_manager = McpManager()
