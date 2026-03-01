import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_ai import RunContext

from app.services.config_service import config_service
from ..base import BaseTool
from .registry import builtin_tool_registry

logger = logging.getLogger(__name__)

DEFAULT_DENY_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\bdel\s+/[fq]\b",
    r"\brmdir\s+/s\b",
    r"(?:^|[;&|]\s*)format\b",
    r"\b(mkfs|diskpart)\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
    r"\b(shutdown|reboot|poweroff)\b",
    r":\(\)\s*\{.*\};\s*:",
]


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    return []


def _as_int(value: Any, default: Optional[int]) -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


@dataclass(frozen=True)
class ExecToolConfig:
    timeout_s: int
    working_dir: Optional[str]
    deny_patterns: List[str]
    allow_patterns: List[str]
    restrict_to_workspace: bool
    path_append: str
    max_output_chars: int
    max_concurrency: Optional[int]
    enable_windows_path_checks: bool
    log_rejections: bool

    @classmethod
    def from_settings(cls, settings: Dict[str, Any]) -> "ExecToolConfig":
        local_mode = _as_bool(settings.get("local_mode"), False)
        deny_patterns = _as_list(settings.get("deny_patterns")) or DEFAULT_DENY_PATTERNS
        allow_patterns = _as_list(settings.get("allow_patterns"))
        timeout_s = _as_int(settings.get("timeout_s"), 60) or 60
        restrict_to_workspace = _as_bool(settings.get("restrict_to_workspace"), True)
        path_append = settings.get("path_append") if isinstance(settings.get("path_append"), str) else ""
        max_output_chars = _as_int(settings.get("max_output_chars"), 10000) or 10000
        max_concurrency = _as_int(settings.get("max_concurrency"), None)
        enable_windows_path_checks = _as_bool(settings.get("enable_windows_path_checks"), True)
        log_rejections = _as_bool(settings.get("log_rejections"), True)
        working_dir = settings.get("working_dir") if isinstance(settings.get("working_dir"), str) else None

        if local_mode:
            allow_patterns = []
            if timeout_s < 180:
                timeout_s = 240
            restrict_to_workspace = True
            if os.name != "nt" and "enable_windows_path_checks" not in settings:
                enable_windows_path_checks = False

        return cls(
            timeout_s=timeout_s,
            working_dir=working_dir,
            deny_patterns=deny_patterns,
            allow_patterns=allow_patterns,
            restrict_to_workspace=restrict_to_workspace,
            path_append=path_append,
            max_output_chars=max_output_chars,
            max_concurrency=max_concurrency,
            enable_windows_path_checks=enable_windows_path_checks,
            log_rejections=log_rejections,
        )


def build_exec_tool_config() -> ExecToolConfig:
    settings = config_service.get_exec_tool_config()
    if not isinstance(settings, dict):
        settings = {}
    return ExecToolConfig.from_settings(settings)


class ExecTool(BaseTool):
    def __init__(self, config: ExecToolConfig):
        parameters = {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
            },
            "required": ["command"],
        }
        super().__init__(
            name="exec",
            description="Execute a shell command and return its output. Use with caution.",
            parameters=parameters,
        )
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrency) if config.max_concurrency else None

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        command = args.get("command") if isinstance(args, dict) else None
        if not command:
            raise ValueError("command is required")
        working_dir = args.get("working_dir") if isinstance(args, dict) else None
        cwd = self._resolve_cwd(working_dir)
        guard_error = self._guard_command(command, cwd)
        if guard_error:
            if self.config.log_rejections:
                logger.warning("ExecTool rejected command: %s", guard_error)
            raise PermissionError(guard_error)
        if self._semaphore:
            async with self._semaphore:
                return await self._run_command(command, cwd)
        return await self._run_command(command, cwd)

    def _resolve_cwd(self, working_dir: Optional[str]) -> str:
        cwd = working_dir or self.config.working_dir or os.getcwd()
        cwd_path = Path(cwd).expanduser().resolve()
        if not cwd_path.exists() or not cwd_path.is_dir():
            raise FileNotFoundError("Working directory not found.")
        return str(cwd_path)

    def _guard_command(self, command: str, cwd: str) -> Optional[str]:
        for pattern in self.config.deny_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return f"Command contains denied pattern: {pattern}"

        if self.config.allow_patterns:
            allowed = any(re.search(pattern, command, re.IGNORECASE) for pattern in self.config.allow_patterns)
            if not allowed:
                return "Command is not in allowlist"
        
        if self.config.restrict_to_workspace:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
            if not os.path.abspath(cwd).startswith(project_root):
                return f"Working directory {cwd} is outside of project root {project_root}"
        
        return None

    async def _run_command(self, command: str, cwd: str) -> str:
        env = os.environ.copy()
        if self.config.path_append:
            env["PATH"] = env.get("PATH", "") + os.pathsep + self.config.path_append

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_s,
            )
        except asyncio.TimeoutError:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            raise TimeoutError(f"Command timed out after {self.config.timeout_s} seconds")

        output_parts = []
        if stdout:
            output_parts.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            stderr_text = stderr.decode("utf-8", errors="replace")
            if stderr_text.strip():
                output_parts.append(f"STDERR:\n{stderr_text}")
        if process.returncode != 0:
            output_parts.append(f"Exit code: {process.returncode}")

        result = "\n".join(output_parts) if output_parts else "(no output)"
        if len(result) > self.config.max_output_chars:
            extra = len(result) - self.config.max_output_chars
            result = result[: self.config.max_output_chars] + f"\n... (truncated, {extra} more chars)"
        return result

# Register the tool
builtin_tool_registry.register(ExecTool(build_exec_tool_config()))
