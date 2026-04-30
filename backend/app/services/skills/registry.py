import os
import logging
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.services.skills.directories import SKILL_LAYER_PRIORITY, SkillDirectoryResolver
from app.services.skills.compatibility import SkillCompatibilityEvaluator
from app.services.skills.models import (
    RuntimeSkillActionDescriptor,
    RuntimeSkillActionInvocationRequest,
    RuntimeSkillActionInvocationResult,
    SkillDirectorySpec,
    SkillPackageSpec,
    SkillSpec,
    SkillSummary,
)
from app.services.skills.parsing import SkillLoader, SkillValidator
from app.services.skills.policy import SkillPolicyGate


logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    In-memory skill index keyed by (name, version).
    """

    def __init__(self, skill_dirs: List[str] = None):
        self.skill_dirs = skill_dirs or []
        self.layered_skill_dirs: List[SkillDirectorySpec] = []
        self._skills: Dict[str, Dict[str, SkillSpec]] = {}
        self._packages: Dict[str, Dict[str, SkillPackageSpec]] = {}
        self._latest_versions: Dict[str, str] = {}
        self._compatibility_evaluator = SkillCompatibilityEvaluator()
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_stop_event = threading.Event()
        self._watch_debounce_ms = 2000
        self._watch_layer = "all"
        self._watch_poll_interval = 1.0
        self._watch_snapshot: Dict[str, float] = {}

    def set_layered_skill_dirs(self, layered_skill_dirs: List[SkillDirectorySpec | Dict[str, str]]):
        normalized: List[SkillDirectorySpec] = []
        for item in layered_skill_dirs:
            if isinstance(item, SkillDirectorySpec):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(SkillDirectorySpec(layer=str(item.get("layer")), path=str(item.get("path"))))
        self.layered_skill_dirs = normalized

    def _infer_layer(self, skill_dir: str) -> str:
        resolved = str(Path(skill_dir).expanduser().resolve())
        if self.layered_skill_dirs:
            for item in self.layered_skill_dirs:
                if str(Path(item.path).expanduser().resolve()) == resolved:
                    return item.layer
        basename = Path(resolved).name.lower()
        if basename == "builtin":
            return "builtin"
        if basename == "user":
            return "user"
        if basename == "workspace":
            return "workspace"
        defaults = {item.path: item.layer for item in SkillDirectoryResolver().resolve()}
        return defaults.get(resolved, "workspace")

    def _get_ordered_skill_directories(self) -> List[SkillDirectorySpec]:
        if self.layered_skill_dirs:
            dirs = self.layered_skill_dirs
        else:
            dirs = [
                SkillDirectorySpec(layer=self._infer_layer(skill_dir), path=str(Path(skill_dir).expanduser().resolve()))
                for skill_dir in self.skill_dirs
            ]
        return sorted(dirs, key=lambda item: SKILL_LAYER_PRIORITY.get(item.layer, -1))

    def _resolve_target_dirs(self, layer: str = "all") -> List[SkillDirectorySpec]:
        ordered = self._get_ordered_skill_directories()
        if layer == "all":
            return ordered
        return [item for item in ordered if item.layer == layer]

    def _build_watch_snapshot(self, layer: str = "all") -> Dict[str, float]:
        snapshot: Dict[str, float] = {}
        for item in self._resolve_target_dirs(layer):
            skill_dir = Path(item.path)
            if not skill_dir.exists():
                continue

            package_roots = {path.parent.resolve() for path in skill_dir.rglob("SKILL.md")}
            tracked_files = set()

            for package_root in package_roots:
                for path in package_root.rglob("*"):
                    if path.is_file():
                        tracked_files.add(path.resolve())

            for path in skill_dir.rglob("*.md"):
                resolved = path.resolve()
                if any(package_root in resolved.parents for package_root in package_roots):
                    continue
                tracked_files.add(resolved)

            for path in tracked_files:
                try:
                    stat = os.stat(path)
                    snapshot[str(path)] = stat.st_mtime
                except OSError:
                    continue
        return snapshot

    def start_runtime_watch(self, layer: str = "all", debounce_ms: int = 2000, poll_interval: float = 1.0):
        self.stop_runtime_watch()
        self._watch_layer = layer
        self._watch_debounce_ms = max(100, int(debounce_ms))
        self._watch_poll_interval = max(0.1, float(poll_interval))
        self._watch_snapshot = self._build_watch_snapshot(layer=self._watch_layer)
        self._watch_stop_event.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()

    def stop_runtime_watch(self):
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_stop_event.set()
            self._watch_thread.join(timeout=2.0)
        self._watch_thread = None
        self._watch_stop_event.clear()

    def _watch_loop(self):
        pending_since: Optional[float] = None
        while not self._watch_stop_event.is_set():
            time.sleep(self._watch_poll_interval)
            current_snapshot = self._build_watch_snapshot(layer=self._watch_layer)
            if current_snapshot != self._watch_snapshot:
                if pending_since is None:
                    pending_since = time.time()
                elapsed_ms = (time.time() - pending_since) * 1000
                if elapsed_ms >= self._watch_debounce_ms:
                    self._watch_snapshot = current_snapshot
                    self.load_all(layer=self._watch_layer)
                    pending_since = None
            else:
                pending_since = None

    def load_all(self, layer: str = "all"):
        self._skills = {}
        self._packages = {}
        self._latest_versions = {}

        ordered_dirs = self._get_ordered_skill_directories()
        self.skill_dirs = [item.path for item in ordered_dirs]
        for skill_dir_spec in ordered_dirs:
            skill_dir = Path(skill_dir_spec.path)
            if not skill_dir.exists():
                logger.warning("Skill directory not found: %s", skill_dir)
                continue

            package_roots = {path.parent.resolve() for path in skill_dir.rglob("SKILL.md")}

            for package_root in sorted(package_roots):
                package = SkillLoader.parse_package(package_root)
                if not package:
                    continue
                package.source_layer = skill_dir_spec.layer
                package.source_dir = str(skill_dir)
                self.register_package(package)

            for path in sorted(skill_dir.rglob("*.md")):
                resolved = path.resolve()
                if any(package_root in resolved.parents for package_root in package_roots):
                    continue
                package = SkillLoader.build_package_from_legacy_markdown(resolved)
                if not package:
                    continue
                package.source_layer = skill_dir_spec.layer
                package.source_dir = str(skill_dir)
                self.register_package(package)

    def register(self, skill: SkillSpec):
        if skill.name not in self._skills:
            self._skills[skill.name] = {}
        availability, missing = self._compute_availability(skill)
        skill.availability = availability
        skill.missing_requirements = missing
        self._skills[skill.name][skill.version] = skill

        current_latest = self._latest_versions.get(skill.name)
        if not current_latest:
            self._latest_versions[skill.name] = skill.version
        else:

            def version_key(version: str):
                return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", version)]

            if version_key(skill.version) > version_key(current_latest):
                self._latest_versions[skill.name] = skill.version

    def register_package(self, package: SkillPackageSpec):
        package_validation = SkillLoader.validate_package(package)
        if package_validation.warnings:
            package.metadata = dict(package.metadata or {})
            package.metadata["package_validation_warnings"] = list(package_validation.warnings)
        if not package_validation.is_valid:
            logger.error(
                "Package validation failed for %s: %s",
                package.manifest_path or package.skill_markdown_path or package.source_path,
                package_validation.errors,
            )
            return

        skill = SkillLoader.package_to_skill_spec(package)
        existing = self.get_skill(skill.name, skill.version)
        if existing:
            existing_layer = existing.source_layer or "unknown"
            existing_dir = existing.source_dir or ""
            skill.override_from = f"{existing_layer}:{existing_dir}"
            package.override_from = skill.override_from

        validation_mode = "compat" if bool((skill.metadata or {}).get("compat_generated")) else "strict"
        validation = SkillValidator.validate(skill, mode=validation_mode)
        if not validation.is_valid:
            logger.error(
                "Skill validation failed for %s: %s",
                package.skill_markdown_path or package.source_path,
                validation.errors,
            )
            return
        if validation.warnings:
            package.metadata = dict(package.metadata or {})
            package.metadata["skill_validation_warnings"] = list(validation.warnings)

        if package.name not in self._packages:
            self._packages[package.name] = {}
        self._packages[package.name][package.version] = package
        self.register(skill)

    def _normalize_os_name(self, value: str) -> str:
        val = (value or "").lower()
        if val in {"mac", "macos", "osx", "darwin"}:
            return "darwin"
        if val in {"win", "windows"}:
            return "windows"
        if val in {"linux"}:
            return "linux"
        return val

    def _compute_availability(self, skill: SkillSpec) -> tuple[bool, Dict[str, List[str]]]:
        report = self._compatibility_evaluator.evaluate_skill(skill)
        missing: Dict[str, List[str]] = {}
        if report.os_mismatch:
            missing["os"] = list(report.os_mismatch)
        if report.missing_bins:
            missing["bins"] = list(report.missing_bins)
        if report.missing_env:
            missing["env"] = list(report.missing_env)
        return report.status == "compatible", missing

    def list_summaries(self) -> List[SkillSummary]:
        summaries = []
        for name in self._skills:
            for version in self._skills[name]:
                skill = self._skills[name][version]
                summaries.append(
                    SkillSummary(
                        name=skill.name,
                        description=skill.description,
                        availability=skill.availability,
                        source_path=skill.source_path,
                        source_layer=skill.source_layer,
                        source_dir=skill.source_dir,
                        override_from=skill.override_from,
                    )
                )
        return summaries

    def get_full_skill(
        self,
        name: str,
        version: str = None,
        *,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Optional[SkillSpec]:
        package = self.get_package_manifest(name, version, provider=provider, model_name=model_name)
        if package:
            full = SkillLoader.package_to_skill_spec(package)
            base = self.get_skill(name, version)
            if base:
                full.availability = base.availability
                full.missing_requirements = base.missing_requirements
                full.source_layer = base.source_layer
                full.source_dir = base.source_dir
                full.override_from = base.override_from
            return full
        return self.get_skill(name, version)

    def get_skill(self, name: str, version: str = None) -> Optional[SkillSpec]:
        if name not in self._skills:
            return None

        if not version:
            version = self._latest_versions.get(name)

        return self._skills[name].get(version)

    def get_package_manifest(
        self,
        name: str,
        version: str = None,
        *,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Optional[SkillPackageSpec]:
        if name not in self._packages:
            return None
        if not version:
            version = self._latest_versions.get(name)
        package = self._packages[name].get(version)
        if not package:
            return None
        return SkillLoader.resolve_package_overlay(package, provider=provider, model_name=model_name)

    def list_package_manifests(self) -> List[SkillPackageSpec]:
        manifests: List[SkillPackageSpec] = []
        for name in self._packages:
            for version in self._packages[name]:
                manifests.append(self._packages[name][version])
        return manifests

    def get_action_descriptors(
        self,
        name: str,
        version: str = None,
        *,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> List[RuntimeSkillActionDescriptor]:
        package = self.get_package_manifest(name, version, provider=provider, model_name=model_name)
        if not package:
            return []
        return [
            RuntimeSkillActionDescriptor(
                id=action.id,
                name=package.name,
                version=package.version,
                tool=action.tool,
                resource=action.resource,
                path=action.path,
                runtime=action.runtime,
                load_tier=action.load_tier,
                safety=action.safety,
                approval_policy=action.approval_policy,
                input_schema=dict(action.input_schema or {}),
                output_schema=dict(action.output_schema or {}),
                metadata=dict(action.metadata or {}),
            )
            for action in package.actions
        ]

    def validate_action_invocation(
        self,
        request: RuntimeSkillActionInvocationRequest,
    ) -> RuntimeSkillActionInvocationResult:
        actions = self.get_action_descriptors(
            request.skill_name,
            request.skill_version,
            provider=request.provider,
            model_name=request.model_name,
        )
        action = next((item for item in actions if item.id == request.action_id), None)
        if not action:
            return RuntimeSkillActionInvocationResult(
                accepted=False,
                skill_name=request.skill_name,
                skill_version=request.skill_version,
                action_id=request.action_id,
                approval_required=False,
                execution_mode="tool_only",
                validation_errors=["Action descriptor not found"],
                metadata={"provider": request.provider, "model_name": request.model_name},
            )

        result = SkillPolicyGate.validate_action_invocation(
            action,
            enabled_tools=request.enabled_tools,
            arguments=request.arguments,
        )
        result.metadata.update(
            {
                "provider": request.provider,
                "model_name": request.model_name,
                "argument_keys": sorted(request.arguments.keys()),
            }
        )
        return result

    def list_skills(self) -> List[SkillSpec]:
        all_specs = []
        for name in self._skills:
            for version in self._skills[name]:
                all_specs.append(self._skills[name][version])
        return all_specs
