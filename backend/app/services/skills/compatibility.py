from __future__ import annotations

import os
import platform
import shutil
from typing import Iterable, List, Optional

from app.services.skills.import_models import SkillCompatibilityReport
from app.services.skills.models import SkillPackageSpec, SkillSpec


def _default_supported_tools() -> set[str]:
    try:
        from app.mcp.builtin import builtin_tool_registry

        return {item["id"] for item in builtin_tool_registry.get_all_metadata() if isinstance(item.get("id"), str)}
    except Exception:
        return set()


class SkillCompatibilityEvaluator:
    def __init__(
        self,
        *,
        supported_tools: Optional[Iterable[str]] = None,
        current_os: Optional[str] = None,
    ):
        if supported_tools is None:
            self.supported_tools = _default_supported_tools()
        else:
            self.supported_tools = set(supported_tools)
        self.current_os = self._normalize_os_name(current_os or platform.system())

    @staticmethod
    def _normalize_os_name(value: str) -> str:
        val = (value or "").lower()
        if val in {"mac", "macos", "osx", "darwin"}:
            return "darwin"
        if val in {"win", "windows"}:
            return "windows"
        if val == "linux":
            return "linux"
        return val

    def _evaluate_common(
        self,
        *,
        required_os: List[str],
        requires_bins: List[str],
        requires_env: List[str],
        declared_tools: List[str],
    ) -> SkillCompatibilityReport:
        issues: List[str] = []
        missing_bins = [item for item in requires_bins if item and shutil.which(item) is None]
        missing_env = [item for item in requires_env if item and not os.getenv(item)]
        normalized_os = [self._normalize_os_name(item) for item in required_os if item]
        os_mismatch: List[str] = []
        if normalized_os and self.current_os not in normalized_os:
            os_mismatch = [self.current_os]
            issues.append(f"Unsupported OS for current runtime: {self.current_os}")
        if missing_bins:
            issues.extend(f"Missing required binary: {item}" for item in missing_bins)
        if missing_env:
            issues.extend(f"Missing required environment variable: {item}" for item in missing_env)

        unsupported_tools = sorted({item for item in declared_tools if item and item not in self.supported_tools})
        issues.extend(f"Unsupported tool required: {item}" for item in unsupported_tools)

        return SkillCompatibilityReport(
            status="compatible" if not issues else "incompatible",
            issues=issues,
            missing_bins=missing_bins,
            missing_env=missing_env,
            unsupported_tools=unsupported_tools,
            os_mismatch=os_mismatch,
        )

    def evaluate_package(self, package: SkillPackageSpec) -> SkillCompatibilityReport:
        requires = package.requires or {}
        required_tools = [action.tool for action in package.actions if action.tool]
        return self._evaluate_common(
            required_os=list(package.os or []),
            requires_bins=list(requires.get("bins") or []),
            requires_env=list(requires.get("env") or []),
            declared_tools=required_tools,
        )

    def evaluate_skill(self, skill: SkillSpec) -> SkillCompatibilityReport:
        requires = skill.requires or {}
        allowed_tools = list(skill.constraints.allowed_tools or []) if skill.constraints and skill.constraints.allowed_tools else []
        return self._evaluate_common(
            required_os=list(skill.os or []),
            requires_bins=list(requires.get("bins") or []),
            requires_env=list(requires.get("env") or []),
            declared_tools=allowed_tools,
        )
