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
from .builtin import builtin_tool_registry

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
            tools.extend(builtin_tool_registry.get_all_metadata())
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


# Global instance
mcp_manager = McpManager()
