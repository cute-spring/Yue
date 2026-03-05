from typing import Dict, List, Optional, Any, Set, Tuple, Callable, Awaitable
import logging
import re
import os
import json
import asyncio
from uuid import uuid4
from dataclasses import replace
from pydantic import ValidationError
from pydantic_ai import Tool, RunContext
from .base import BaseTool, McpTool, BuiltinTool
from .schema_translator import to_provider_schema
from .manager import mcp_manager, McpManager
from .builtin import builtin_tool_registry
from app.services.agent_store import agent_store

logger = logging.getLogger(__name__)

# Callback type for tool events
ToolEventCallback = Callable[[Dict[str, Any]], Awaitable[None]]

class ToolRegistry:
    def __init__(self, mcp_manager: McpManager):
        self.mcp_manager = mcp_manager
        
    async def get_tools_for_agent(self, agent_id: Optional[str], enabled_tools: Optional[List[str]] = None) -> List[BaseTool]:
        """
        Get all authorized tools for an agent, returned as BaseTool objects.
        """
        agent = agent_store.get_agent(agent_id) if agent_id else None

        if not agent and not enabled_tools:
            logger.info("No agent context or enabled tools provided. Returning zero tools for safety.")
            return []

        allowed_tools = set(enabled_tools if enabled_tools is not None else (agent.enabled_tools if agent else []))
        tools: List[BaseTool] = []

        # 1. Get MCP tools
        mcp_tools = await self._get_mcp_tools(allowed_tools)
        tools.extend(mcp_tools)

        # 2. Get Built-in tools
        builtin_tools = await self._get_builtin_tools(allowed_tools)
        tools.extend(builtin_tools)

        if self._shadow_mode_enabled():
            await self._shadow_compare(agent_id, tools, allowed_tools)

        return tools

    async def get_pydantic_ai_tools_for_agent(
        self, 
        agent_id: Optional[str], 
        provider: Optional[str] = None,
        on_event: Optional[ToolEventCallback] = None,
        enabled_tools: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Get all authorized tools for an agent, converted to Pydantic AI Tool objects.
        
        Args:
            agent_id: The ID of the agent.
            provider: The LLM provider (e.g., "openai", "deepseek").
            on_event: Optional callback for tool events (started, finished).
            enabled_tools: Optional explicit list of tool names (overrides agent's list).
        """
        base_tools = await self.get_tools_for_agent(agent_id, enabled_tools=enabled_tools)
        pydantic_tools = []
        for tool in base_tools:
            if isinstance(tool, McpTool):
                # Apply special LLM name formatting for MCP tools to avoid conflicts
                sanitized_server = re.sub(r'[^a-zA-Z0-9_-]', '_', tool.server_name)
                sanitized_tool = re.sub(r'[^a-zA-Z0-9_-]', '_', tool.name)
                llm_tool_name = f"mcp__{sanitized_server}__{sanitized_tool}"
                pydantic_tools.append(self._to_pydantic_ai_tool(tool, llm_name=llm_tool_name, provider=provider, on_event=on_event))
            else:
                pydantic_tools.append(self._to_pydantic_ai_tool(tool, provider=provider, on_event=on_event))
        return pydantic_tools

    def _to_pydantic_ai_tool(
        self, 
        tool: BaseTool, 
        llm_name: Optional[str] = None, 
        provider: Optional[str] = None,
        on_event: Optional[ToolEventCallback] = None
    ) -> Tool:
        tool_name = llm_name or tool.name
        ArgsModel = tool.build_args_model()

        async def wrapper(ctx: RunContext, args: ArgsModel) -> str:
            call_id = f"call_{uuid4().hex[:8]}"
            start_time = asyncio.get_event_loop().time()
            
            # Emit tool.call.started event
            if on_event:
                try:
                    await on_event({
                        "event": "tool.call.started",
                        "call_id": call_id,
                        "tool_name": tool_name,
                        "args": tool.validate_params(args)
                    })
                except Exception:
                    logger.exception("Error emitting tool.call.started event")

            try:
                validated_args = tool.validate_params(args)
                result = await tool.execute(ctx, validated_args)
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                # Emit tool.call.finished event
                if on_event:
                    try:
                        await on_event({
                            "event": "tool.call.finished",
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "result": result,
                            "duration_ms": duration_ms
                        })
                    except Exception:
                        logger.exception("Error emitting tool.call.finished event")
                
                return result
            except Exception as e:
                error_res = self._handle_tool_error(tool, e)
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                # Emit tool.call.finished event with error
                if on_event:
                    try:
                        await on_event({
                            "event": "tool.call.finished",
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "error": str(e),
                            "result": error_res,
                            "duration_ms": duration_ms
                        })
                    except Exception:
                        logger.exception("Error emitting tool.call.finished event on error")
                
                return error_res

        prepare = None
        if provider:
            async def prepare(ctx: RunContext, tool_def):
                schema = to_provider_schema(provider, tool.parameters)
                return replace(tool_def, parameters_json_schema=schema)
        return Tool(wrapper, name=tool_name, description=tool.description, prepare=prepare)

    def _handle_tool_error(self, tool: BaseTool, error: Exception) -> str:
        logger.exception("Tool execution failed: %s", tool.name)
        error_code, message, hint = self._classify_tool_error(error)
        payload = {
            "error_code": error_code,
            "message": message,
            "hint": hint,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _classify_tool_error(self, error: Exception) -> Tuple[str, str, str]:
        error_msg = str(error)
        error_msg_lower = error_msg.lower()

        if isinstance(error, (ValidationError, TypeError, ValueError)):
            if "missing" in error_msg_lower or "required" in error_msg_lower:
                return (
                    "tool_param_missing",
                    "Missing required tool parameters.",
                    "Please provide all required parameters.",
                )
            return (
                "tool_param_invalid",
                "Invalid tool parameters.",
                "Check parameter types and schema.",
            )

        if isinstance(error, FileNotFoundError) or "no such file" in error_msg_lower or "not found" in error_msg_lower:
            return (
                "tool_not_found",
                "Requested resource was not found.",
                "Try listing the parent directory or verify the path.",
            )

        if isinstance(error, PermissionError) or "permission" in error_msg_lower or "access denied" in error_msg_lower:
            return (
                "tool_permission_denied",
                "Permission denied for the requested resource.",
                "Use paths within allowed roots.",
            )

        if isinstance(error, TimeoutError) or "timeout" in error_msg_lower:
            return (
                "tool_timeout",
                "Tool execution timed out.",
                "Reduce scope or retry with a smaller query.",
            )

        return (
            "tool_execution_error",
            "Tool execution failed.",
            "Retry with simpler inputs or verify parameters.",
        )

    async def get_all_available_tools_metadata(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all available tools from both MCP and built-in sources.
        Used for UI configuration and tool selection.
        This provides a single source of truth for both display and execution.
        """
        # We can pass an "allow all" set or modify internal methods
        # To avoid complex logic, we'll implement a clean version here
        tools_meta = []
        
        # 1. Built-in tools
        tools_meta.extend(builtin_tool_registry.get_all_metadata())
            
        # 2. MCP tools
        for name, session in self.mcp_manager.sessions.items():
            try:
                if getattr(session, "is_closed", False):
                    continue
                result = await session.list_tools()
                for tool_def in result.tools:
                    tools_meta.append({
                        "id": f"{name}:{tool_def.name}",
                        "name": tool_def.name,
                        "description": tool_def.description,
                        "server": name,
                        "input_schema": tool_def.inputSchema
                    })
            except Exception:
                logger.exception(f"Error listing tools for MCP server in metadata: {name}")
                
        return sorted(tools_meta, key=lambda t: (t.get("server", ""), t.get("name", "")))

    async def _get_mcp_tools(self, allowed_tools: Set[str]) -> List[McpTool]:
        mcp_tools = []
        for name, session in self.mcp_manager.sessions.items():
            try:
                if getattr(session, "is_closed", False):
                    continue
                result = await session.list_tools()
                for tool_def in result.tools:
                    composite_id = f"{name}:{tool_def.name}"
                    if composite_id in allowed_tools or tool_def.name in allowed_tools:
                        mcp_tool = McpTool(
                            server_name=name,
                            session=session,
                            name=tool_def.name,
                            description=tool_def.description,
                            parameters=tool_def.inputSchema
                        )
                        mcp_tools.append(mcp_tool)
            except Exception:
                logger.exception(f"Error listing tools for MCP server: {name}")
        return mcp_tools

    async def _get_builtin_tools(self, allowed_tools: Set[str]) -> List[BuiltinTool]:
        builtin_tools = []
        for tool in builtin_tool_registry.get_all_tools():
            composite_id = f"builtin:{tool.name}"
            if composite_id in allowed_tools or tool.name in allowed_tools:
                # BuiltinTool is a BaseTool subclass in mcp/base.py
                # but we need to ensure it's compatible with registry expectation
                builtin_tools.append(tool)
        return builtin_tools

    def _shadow_mode_enabled(self) -> bool:
        val = (os.getenv("MCP_TOOL_SHADOW_MODE") or "").strip().lower()
        return val in {"1", "true", "yes", "on"}

    async def _shadow_compare(self, agent_id: Optional[str], tools: List[BaseTool], allowed_tools: Set[str]) -> None:
        try:
            legacy = await self._get_legacy_tool_meta(allowed_tools)
            current = self._get_current_tool_meta(tools)
            self._compare_tool_meta(agent_id, current, legacy)
        except Exception:
            logger.exception("Shadow compare failed for agent_id=%s", agent_id)

    async def _get_legacy_tool_meta(self, allowed_tools: Set[str]) -> List[Dict[str, Any]]:
        items = await self.mcp_manager.get_available_tools()
        out = []
        for t in items:
            tid = t.get("id")
            name = t.get("name")
            if not tid or not name:
                continue
            if tid in allowed_tools or name in allowed_tools:
                out.append({
                    "id": tid,
                    "name": name,
                    "server": t.get("server"),
                    "input_schema": t.get("input_schema") or {},
                })
        return out

    def _get_current_tool_meta(self, tools: List[BaseTool]) -> List[Dict[str, Any]]:
        out = []
        for tool in tools:
            if isinstance(tool, McpTool):
                tid = f"{tool.server_name}:{tool.name}"
                server = tool.server_name
            else:
                tid = f"builtin:{tool.name}"
                server = "builtin"
            out.append({
                "id": tid,
                "name": tool.name,
                "server": server,
                "input_schema": tool.parameters or {},
            })
        return out

    def _compare_tool_meta(self, agent_id: Optional[str], current: List[Dict[str, Any]], legacy: List[Dict[str, Any]]) -> None:
        current_ids = [t["id"] for t in current]
        legacy_ids = [t["id"] for t in legacy]
        current_set = set(current_ids)
        legacy_set = set(legacy_ids)

        missing = sorted(legacy_set - current_set)
        extra = sorted(current_set - legacy_set)

        order_same = current_ids == legacy_ids

        schema_mismatch = []
        legacy_by_id = {t["id"]: t for t in legacy}
        for t in current:
            other = legacy_by_id.get(t["id"])
            if not other:
                continue
            if self._normalize_schema(t.get("input_schema")) != self._normalize_schema(other.get("input_schema")):
                schema_mismatch.append(t["id"])

        if missing or extra or not order_same or schema_mismatch:
            logger.warning(
                "Tool shadow mismatch agent_id=%s missing=%s extra=%s order_same=%s schema_mismatch=%s",
                agent_id,
                missing[:20],
                extra[:20],
                order_same,
                schema_mismatch[:20],
            )
        else:
            logger.info("Tool shadow match agent_id=%s count=%d", agent_id, len(current_ids))

    def _normalize_schema(self, schema: Any) -> str:
        try:
            return json.dumps(schema or {}, sort_keys=True, ensure_ascii=False)
        except Exception:
            return str(schema or {})

# Global registry instance
tool_registry = ToolRegistry(mcp_manager)
