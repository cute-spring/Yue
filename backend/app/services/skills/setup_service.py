from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from app.mcp.builtin.exec import build_exec_tool_config, run_exec_argv
from app.services.skills.import_models import SetupAuditEntry, SkillPreflightRecord
from app.services.skills.import_store import SkillImportStore
from app.services.skills.setup_models import InstallSetupSpec, SetupValidationResult

_DISALLOWED_CHARS = ("\n", "\r", ";", "&&", "||", "|", "`", "$(", ">", "<", "&")
_GLOBAL_INSTALL_FLAGS = {"--user", "-g", "--global"}
_PATH_FLAGS = {"-r", "--requirement", "--prefix", "--dir", "--cwd"}
_PYTHON_EXECUTABLES = {"python", "pip", "uv"}
_NODE_EXECUTABLES = {"npm", "pnpm", "yarn"}
_DEFAULT_NODE_PREFIX = Path(".yue/node")
_DEFAULT_PYTHON_VENV = Path(".yue/python/venv")


def _default_runner(*, command: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    result = run_exec_argv(command, cwd)
    return result


class SkillSetupService:
    def __init__(
        self,
        *,
        import_store: SkillImportStore | None = None,
        command_runner: Optional[Callable[..., subprocess.CompletedProcess[str]]] = None,
    ):
        self.import_store = import_store or SkillImportStore()
        self._command_runner = command_runner or _default_runner
        self._exec_config = build_exec_tool_config()

    @staticmethod
    def parse_install_setup(install: object) -> SetupValidationResult:
        if not isinstance(install, dict):
            return SetupValidationResult(valid=False, errors=["install block must be an object"])
        setup = install.get("setup")
        if not isinstance(setup, dict):
            return SetupValidationResult(valid=False, errors=["install.setup block is missing"])
        runtime = setup.get("runtime")
        commands = setup.get("commands")
        errors: list[str] = []
        if runtime not in {"python", "node"}:
            errors.append("install.setup.runtime must be one of: python, node")
        if not isinstance(commands, list) or not commands or not all(isinstance(item, str) and item.strip() for item in commands):
            errors.append("install.setup.commands must be a non-empty list of command strings")
        if errors:
            return SetupValidationResult(valid=False, errors=errors)
        return SetupValidationResult(valid=True, setup=InstallSetupSpec(runtime=runtime, commands=[item.strip() for item in commands]))

    @staticmethod
    def compute_package_fingerprint(source_path: str) -> str:
        root = Path(source_path).expanduser().resolve()
        hasher = hashlib.sha256()
        if root.is_file():
            hasher.update(root.name.encode("utf-8"))
            hasher.update(root.read_bytes())
            return f"sha256:{hasher.hexdigest()}"

        for path in sorted(item for item in root.rglob("*") if item.is_file() and ".yue" not in item.parts):
            rel = path.relative_to(root).as_posix()
            hasher.update(rel.encode("utf-8"))
            hasher.update(path.read_bytes())
        return f"sha256:{hasher.hexdigest()}"

    @staticmethod
    def isolated_env_path_for(runtime: str, source_path: str) -> str:
        root = SkillSetupService._skill_root(source_path)
        if runtime == "python":
            return str(root / _DEFAULT_PYTHON_VENV)
        return str(root / _DEFAULT_NODE_PREFIX)

    @staticmethod
    def _skill_root(source_path: str) -> Path:
        path = Path(source_path).expanduser().resolve()
        return path if path.is_dir() else path.parent

    @staticmethod
    def _is_within(root: Path, candidate: Path) -> bool:
        try:
            candidate.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    def _validate_platform_patterns(self, command: str) -> None:
        for pattern in self._exec_config.deny_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")

    def _resolve_token_path(self, root: Path, token: str) -> Path:
        token_path = Path(token)
        resolved = token_path.expanduser().resolve() if token_path.is_absolute() else (root / token_path).resolve()
        if not self._is_within(root, resolved):
            raise RuntimeError(f"setup command rejected by Phase 1 policy: {token}")
        return resolved

    def _validate_common_command(self, command: str, runtime: str, source_path: str) -> tuple[list[str], Path, Path]:
        if any(token in command for token in _DISALLOWED_CHARS):
            raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
        self._validate_platform_patterns(command)
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}") from exc
        if not tokens:
            raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")

        root = self._skill_root(source_path)
        env_root = Path(self.isolated_env_path_for(runtime, source_path)).resolve()

        executable = tokens[0]
        executable_name = Path(executable).name
        allowed_executables = _PYTHON_EXECUTABLES if runtime == "python" else _NODE_EXECUTABLES
        if executable_name not in allowed_executables:
            raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
        if "/" in executable or executable.startswith("."):
            exec_path = self._resolve_token_path(root, executable)
            if executable_name == "pip" and exec_path != (root / _DEFAULT_PYTHON_VENV / "bin" / "pip").resolve():
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            if executable_name == "python" and exec_path != (root / _DEFAULT_PYTHON_VENV / "bin" / "python").resolve():
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")

        for index, token in enumerate(tokens[1:], start=1):
            if token in _GLOBAL_INSTALL_FLAGS or token in {"-c", "-e"}:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            if token in _PATH_FLAGS and index + 1 < len(tokens):
                self._resolve_token_path(root, tokens[index + 1])
            elif token.startswith("/") or token.startswith("."):
                self._resolve_token_path(root, token)
        return tokens, root, env_root

    def _validate_python_command(self, tokens: list[str], root: Path, env_root: Path, command: str) -> list[str]:
        executable_name = Path(tokens[0]).name
        env_python = (root / _DEFAULT_PYTHON_VENV / "bin" / "python").resolve()
        env_pip = (root / _DEFAULT_PYTHON_VENV / "bin" / "pip").resolve()

        if executable_name == "python" and tokens[:3] == ["python", "-m", "venv"]:
            if len(tokens) != 4 or self._resolve_token_path(root, tokens[3]) != env_root:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            return tokens

        if executable_name == "python":
            exec_path = (root / tokens[0]).resolve() if ("/" in tokens[0] or tokens[0].startswith(".")) else None
            if exec_path != env_python:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            if tokens[1:4] != ["-m", "pip", "install"]:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            return tokens

        if executable_name == "pip":
            exec_path = self._resolve_token_path(root, tokens[0]) if ("/" in tokens[0] or tokens[0].startswith(".")) else None
            if exec_path != env_pip or "install" not in tokens[1:]:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            return tokens

        raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")

    def _validate_node_command(self, tokens: list[str], root: Path, env_root: Path, command: str) -> list[str]:
        executable_name = Path(tokens[0]).name
        if executable_name == "npm":
            if "install" not in tokens[1:] or "--prefix" not in tokens:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            prefix_path = self._resolve_token_path(root, tokens[tokens.index("--prefix") + 1])
            if prefix_path != env_root:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            return tokens

        if executable_name == "pnpm":
            if "install" not in tokens[1:] or "--dir" not in tokens:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            dir_path = self._resolve_token_path(root, tokens[tokens.index("--dir") + 1])
            if dir_path != env_root:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            return tokens

        if executable_name == "yarn":
            if "install" not in tokens[1:] or "--cwd" not in tokens:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            cwd_path = self._resolve_token_path(root, tokens[tokens.index("--cwd") + 1])
            if cwd_path != env_root:
                raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")
            return tokens

        raise RuntimeError(f"setup command rejected by Phase 1 policy: {command}")

    def _validate_command(self, command: str, runtime: str, source_path: str) -> tuple[list[str], str]:
        tokens, root, env_root = self._validate_common_command(command, runtime, source_path)
        validated = (
            self._validate_python_command(tokens, root, env_root, command)
            if runtime == "python"
            else self._validate_node_command(tokens, root, env_root, command)
        )
        cwd = str(root if runtime == "python" else env_root)
        return validated, cwd

    def _refresh_current_fingerprint(self, item: SkillPreflightRecord) -> str:
        return self.compute_package_fingerprint(item.source_path)

    def trust_skill(self, skill_ref: str) -> SkillPreflightRecord:
        item = self.import_store.get_preflight_record(skill_ref)
        if item is None:
            raise KeyError("skill_preflight_not_found")
        if not item.setup_capable:
            raise ValueError("skill_setup_not_supported")
        current_fingerprint = self._refresh_current_fingerprint(item)
        if item.package_fingerprint and item.package_fingerprint != current_fingerprint:
            item.trust_status = "untrusted"
            item.setup_last_error = "Package contents changed since preflight."
            self.import_store.save_preflight_record(item)
            raise RuntimeError("skill_setup_requires_rescan")
        item.package_fingerprint = current_fingerprint
        item.trust_status = "trusted"
        if item.setup_status == "not_needed":
            item.setup_status = "available"
        self.import_store.save_preflight_record(item)
        return item

    def get_setup_state(self, skill_ref: str) -> SkillPreflightRecord:
        item = self.import_store.get_preflight_record(skill_ref)
        if item is None:
            raise KeyError("skill_preflight_not_found")
        return item

    def _ensure_trusted_fingerprint(self, item: SkillPreflightRecord) -> None:
        current_fingerprint = self._refresh_current_fingerprint(item)
        if item.package_fingerprint != current_fingerprint:
            item.trust_status = "untrusted"
            item.setup_status = "available"
            item.package_fingerprint = current_fingerprint
            item.setup_last_error = "Package contents changed since trust approval."
            self.import_store.save_preflight_record(item)
            raise PermissionError("skill_setup_requires_trust")

    def run_setup(self, skill_ref: str) -> SkillPreflightRecord:
        item = self.import_store.get_preflight_record(skill_ref)
        if item is None:
            raise KeyError("skill_preflight_not_found")
        if not item.setup_capable:
            raise ValueError("skill_setup_not_supported")
        if item.trust_status != "trusted":
            raise PermissionError("skill_setup_requires_trust")
        self._ensure_trusted_fingerprint(item)
        setup = InstallSetupSpec(runtime=item.setup_runtime or "python", commands=list(item.last_setup_commands or []))
        if not setup.commands:
            raise ValueError("skill_setup_contract_invalid")

        item.setup_status = "running"
        item.setup_last_error = None
        item.setup_audit_entries = []
        item.last_setup_started_at = datetime.utcnow()
        self.import_store.save_preflight_record(item)

        try:
            for command in setup.commands:
                argv, cwd = self._validate_command(command, setup.runtime, item.source_path)
                Path(cwd).mkdir(parents=True, exist_ok=True)
                started_at = datetime.utcnow()
                result = self._command_runner(command=argv, cwd=cwd)
                finished_at = datetime.utcnow()
                duration_ms = round((finished_at - started_at).total_seconds() * 1000)
                entry = SetupAuditEntry(
                    command=command,
                    argv=argv,
                    cwd=cwd,
                    exit_code=result.returncode,
                    stdout_size=len(result.stdout or ""),
                    stderr_size=len(result.stderr or ""),
                    duration_ms=duration_ms,
                    started_at=started_at,
                    finished_at=finished_at,
                )
                item.setup_audit_entries.append(entry)
                if result.returncode != 0:
                    err = (result.stderr or result.stdout or "").strip()
                    raise RuntimeError(err or f"setup command failed: {command}")
            item.setup_status = "succeeded"
            item.setup_last_error = None
        except Exception as exc:
            item.setup_status = "failed"
            item.setup_last_error = str(exc)
        finally:
            item.last_setup_finished_at = datetime.utcnow()
            self.import_store.save_preflight_record(item)
        return item
