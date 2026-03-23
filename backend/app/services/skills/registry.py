import logging
import os
import platform
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.skills.directories import SKILL_LAYER_PRIORITY, SkillDirectoryResolver
from app.services.skills.models import SkillDirectorySpec, SkillSpec, SkillSummary
from app.services.skills.parsing import SkillLoader, SkillValidator


logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    In-memory skill index keyed by (name, version).
    """

    def __init__(self, skill_dirs: List[str] = None):
        self.skill_dirs = skill_dirs or []
        self.layered_skill_dirs: List[SkillDirectorySpec] = []
        self._skills: Dict[str, Dict[str, SkillSpec]] = {}
        self._latest_versions: Dict[str, str] = {}
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
            if not os.path.exists(item.path):
                continue
            for root, _, files in os.walk(item.path):
                for file in files:
                    if not file.endswith(".md"):
                        continue
                    file_path = os.path.join(root, file)
                    try:
                        stat = os.stat(file_path)
                        snapshot[file_path] = stat.st_mtime
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
        self._latest_versions = {}

        ordered_dirs = self._get_ordered_skill_directories()
        self.skill_dirs = [item.path for item in ordered_dirs]
        for skill_dir_spec in ordered_dirs:
            skill_dir = skill_dir_spec.path
            if not os.path.exists(skill_dir):
                logger.warning("Skill directory not found: %s", skill_dir)
                continue

            package_roots = set()
            for root, _, files in os.walk(skill_dir):
                if "SKILL.md" in files:
                    package_roots.add(root)

            for root, _, files in os.walk(skill_dir):
                for file in files:
                    if file.endswith(".md"):
                        if self._should_skip_file(root, file, package_roots):
                            continue
                        path = os.path.join(root, file)
                        with open(path, "r") as file_obj:
                            content = file_obj.read()

                        spec = SkillLoader.parse_markdown(content, source_path=path)
                        if spec:
                            result = SkillValidator.validate(spec)
                            if result.is_valid:
                                spec.source_layer = skill_dir_spec.layer
                                spec.source_dir = skill_dir
                                existing = self.get_skill(spec.name, spec.version)
                                if existing:
                                    existing_layer = existing.source_layer or "unknown"
                                    existing_dir = existing.source_dir or ""
                                    spec.override_from = f"{existing_layer}:{existing_dir}"
                                self.register(spec)
                            else:
                                logger.error("Skill validation failed for %s: %s", path, result.errors)

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

    def _should_skip_file(self, root: str, file: str, package_roots: set) -> bool:
        if not package_roots:
            return False
        for package_root in package_roots:
            try:
                if os.path.commonpath([root, package_root]) != package_root:
                    continue
            except ValueError:
                continue
            if root == package_root:
                return file != "SKILL.md"
            return True
        return False

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
        missing: Dict[str, List[str]] = {}
        os_allowed = [self._normalize_os_name(o) for o in (skill.os or []) if o]
        current_os = self._normalize_os_name(platform.system())
        if os_allowed and current_os not in os_allowed:
            missing["os"] = [current_os]

        requires = skill.requires or {}
        bins = requires.get("bins") or []
        env = requires.get("env") or []
        missing_bins = [b for b in bins if b and shutil.which(b) is None]
        missing_env = [e for e in env if e and not os.getenv(e)]
        if missing_bins:
            missing["bins"] = missing_bins
        if missing_env:
            missing["env"] = missing_env
        return len(missing) == 0, missing

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

    def get_full_skill(self, name: str, version: str = None) -> Optional[SkillSpec]:
        base = self.get_skill(name, version)
        if not base:
            return None
        if not base.source_path or not os.path.exists(base.source_path):
            return base
        with open(base.source_path, "r") as file_obj:
            content = file_obj.read()
        full = SkillLoader.parse_markdown(content, source_path=base.source_path)
        if not full:
            return base
        full.availability = base.availability
        full.missing_requirements = base.missing_requirements
        return full

    def get_skill(self, name: str, version: str = None) -> Optional[SkillSpec]:
        if name not in self._skills:
            return None

        if not version:
            version = self._latest_versions.get(name)

        return self._skills[name].get(version)

    def list_skills(self) -> List[SkillSpec]:
        all_specs = []
        for name in self._skills:
            for version in self._skills[name]:
                all_specs.append(self._skills[name][version])
        return all_specs
