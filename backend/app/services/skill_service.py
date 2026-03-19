import os
import yaml
import logging
import re
import platform
import shutil
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from app.services.skill_group_store import skill_group_store

logger = logging.getLogger(__name__)

SKILL_LAYER_PRIORITY = {
    "builtin": 0,
    "workspace": 1,
    "user": 2,
}

class SkillDirectorySpec(BaseModel):
    layer: str
    path: str

class SkillConstraints(BaseModel):
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    allowed_tools: Optional[List[str]] = None

class SkillSpec(BaseModel):
    name: str
    version: str
    description: str
    capabilities: List[str]
    entrypoint: str
    inputs_schema: Optional[Dict[str, Any]] = None
    outputs_schema: Optional[Dict[str, Any]] = None
    constraints: Optional[SkillConstraints] = None
    compatibility: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    requires: Optional[Dict[str, List[str]]] = None
    os: Optional[List[str]] = None
    install: Optional[Dict[str, Any]] = None
    homepage: Optional[str] = None
    emoji: Optional[str] = None
    always: Optional[bool] = None
    availability: Optional[bool] = True
    missing_requirements: Optional[Dict[str, List[str]]] = None
    
    # Sections parsed from Markdown
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    examples: Optional[str] = None
    failure_handling: Optional[str] = None
    
    # Metadata
    source_path: Optional[str] = None
    source_layer: Optional[str] = None
    source_dir: Optional[str] = None
    override_from: Optional[str] = None

class SkillSummary(BaseModel):
    name: str
    description: str
    availability: Optional[bool] = True
    source_path: Optional[str] = None
    source_layer: Optional[str] = None
    source_dir: Optional[str] = None
    override_from: Optional[str] = None

class SkillDirectoryResolver:
    def __init__(
        self,
        builtin_dir: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        user_dir: Optional[str] = None,
    ):
        backend_root = Path(__file__).resolve().parents[2]
        workspace_root = Path(__file__).resolve().parents[3]
        resolved_user_dir = user_dir or os.getenv("YUE_USER_SKILLS_DIR") or str(Path.home() / ".yue" / "skills")
        self.builtin_dir = str(Path(builtin_dir or (backend_root / "data" / "skills")).resolve())
        self.workspace_dir = str(Path(workspace_dir or (workspace_root / "data" / "skills")).resolve())
        self.user_dir = str(Path(resolved_user_dir).expanduser().resolve())

    def resolve(self) -> List[SkillDirectorySpec]:
        return [
            SkillDirectorySpec(layer="builtin", path=self.builtin_dir),
            SkillDirectorySpec(layer="workspace", path=self.workspace_dir),
            SkillDirectorySpec(layer="user", path=self.user_dir),
        ]

class RuntimeCapabilityDescriptor(BaseModel):
    prompt_blocks: Dict[str, str] = Field(default_factory=dict)
    tool_policy: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    source_type: str  # "legacy_agent" or "markdown_skill"
    name: str
    version: str

class SkillValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class SkillLoader:
    """
    Discovery, parse, and normalize skills from Markdown files.
    """
    @staticmethod
    def parse_markdown(content: str, source_path: str = None) -> Optional[SkillSpec]:
        try:
            # 1. Split frontmatter and sections
            # Expecting format:
            # ---
            # name: ...
            # ---
            # ## Section Name
            # ...
            
            parts = re.split(r'^---\s*$', content, flags=re.MULTILINE)
            if len(parts) < 3:
                logger.error(f"Invalid skill format in {source_path}: missing frontmatter delimiters")
                return None
            
            frontmatter_raw = parts[1].strip()
            markdown_content = "---".join(parts[2:]).strip()
            
            # 2. Parse frontmatter
            frontmatter = yaml.safe_load(frontmatter_raw)
            if not isinstance(frontmatter, dict):
                logger.error(f"Invalid frontmatter in {source_path}")
                return None
            
            def normalize_list(value: Any) -> List[str]:
                if value is None:
                    return []
                if isinstance(value, list):
                    return [str(v).strip() for v in value if v is not None and str(v).strip()]
                if isinstance(value, str):
                    val = value.strip()
                    return [val] if val else []
                return []

            raw_requires = frontmatter.get("requires")
            requires = None
            if isinstance(raw_requires, dict):
                bins = normalize_list(raw_requires.get("bins") or raw_requires.get("bin"))
                env = normalize_list(raw_requires.get("env"))
                requires = {"bins": bins, "env": env}
            elif isinstance(raw_requires, list) or isinstance(raw_requires, str):
                requires = {"bins": normalize_list(raw_requires), "env": []}

            raw_os = frontmatter.get("os")
            os_list = normalize_list(raw_os)
            os_list = [o.lower() for o in os_list] if os_list else None

            metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else None
            install = frontmatter.get("install") if isinstance(frontmatter.get("install"), dict) else None

            # 3. Parse sections
            sections = {}
            current_section = None
            section_content = []
            
            for line in markdown_content.splitlines():
                match = re.match(r'^##\s+(.+)$', line)
                if match:
                    if current_section:
                        sections[current_section] = "\n".join(section_content).strip()
                    current_section = match.group(1).strip().lower().replace(" ", "_")
                    section_content = []
                elif current_section:
                    section_content.append(line)
            
            if current_section:
                sections[current_section] = "\n".join(section_content).strip()
            
            # 4. Create SkillSpec
            skill_data = {**frontmatter}
            skill_data["system_prompt"] = sections.get("system_prompt")
            skill_data["instructions"] = sections.get("instructions")
            skill_data["examples"] = sections.get("examples")
            skill_data["failure_handling"] = sections.get("failure_handling")
            skill_data["source_path"] = source_path
            skill_data["requires"] = requires
            skill_data["os"] = os_list
            skill_data["metadata"] = metadata
            skill_data["install"] = install
            
            return SkillSpec(**skill_data)
        except Exception as e:
            logger.exception(f"Error parsing skill in {source_path}: {e}")
            return None

class SkillValidator:
    """
    Schema and policy validation for skills.
    """
    @staticmethod
    def validate(skill: SkillSpec) -> SkillValidationResult:
        errors = []
        warnings = []
        
        if not skill.name:
            errors.append("Skill name is required")
        if not skill.version:
            errors.append("Skill version is required")
        if not skill.entrypoint:
            errors.append("Skill entrypoint is required")
        
        # Check if entrypoint exists in sections
        entrypoint_attr = skill.entrypoint.lower().replace(" ", "_")
        if not getattr(skill, entrypoint_attr, None):
            errors.append(f"Entrypoint section '{skill.entrypoint}' not found in Markdown")
        
        # Section completeness
        if skill.system_prompt and len(skill.system_prompt.strip()) < 10:
            warnings.append("System prompt is very short")
        
        # Schema validation
        if skill.inputs_schema is not None and not isinstance(skill.inputs_schema, dict):
            errors.append("inputs_schema must be a dictionary")
        if skill.outputs_schema is not None and not isinstance(skill.outputs_schema, dict):
            errors.append("outputs_schema must be a dictionary")
            
        # Constraints validation
        if skill.constraints:
            if skill.constraints.allowed_tools is not None:
                if not isinstance(skill.constraints.allowed_tools, list):
                    errors.append("constraints.allowed_tools must be a list")
                else:
                    for tool in skill.constraints.allowed_tools:
                        if not isinstance(tool, str):
                            errors.append(f"Invalid tool name in allowed_tools: {tool}")
            
        return SkillValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

class SkillRegistry:
    """
    In-memory skill index keyed by (name, version).
    """
    def __init__(self, skill_dirs: List[str] = None):
        self.skill_dirs = skill_dirs or []
        self.layered_skill_dirs: List[SkillDirectorySpec] = []
        self._skills: Dict[str, Dict[str, SkillSpec]] = {} # name -> {version -> spec}
        self._latest_versions: Dict[str, str] = {} # name -> latest_version
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
                logger.warning(f"Skill directory not found: {skill_dir}")
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
                        with open(path, "r") as f:
                            content = f.read()
                        
                        spec = SkillLoader.parse_markdown(content, source_path=path)
                        if spec:
                            res = SkillValidator.validate(spec)
                            if res.is_valid:
                                spec.source_layer = skill_dir_spec.layer
                                spec.source_dir = skill_dir
                                existing = self.get_skill(spec.name, spec.version)
                                if existing:
                                    existing_layer = existing.source_layer or "unknown"
                                    existing_dir = existing.source_dir or ""
                                    spec.override_from = f"{existing_layer}:{existing_dir}"
                                self.register(spec)
                            else:
                                logger.error(f"Skill validation failed for {path}: {res.errors}")

    def register(self, skill: SkillSpec):
        if skill.name not in self._skills:
            self._skills[skill.name] = {}
        availability, missing = self._compute_availability(skill)
        skill.availability = availability
        skill.missing_requirements = missing
        self._skills[skill.name][skill.version] = skill
        
        # Update latest version using semantic comparison
        current_latest = self._latest_versions.get(skill.name)
        if not current_latest:
            self._latest_versions[skill.name] = skill.version
        else:
            # Simple semantic version comparison (split by dots)
            def version_key(v):
                return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', v)]
            
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
                summaries.append(SkillSummary(
                    name=skill.name,
                    description=skill.description,
                    availability=skill.availability,
                    source_path=skill.source_path,
                    source_layer=skill.source_layer,
                    source_dir=skill.source_dir,
                    override_from=skill.override_from,
                ))
        return summaries

    def get_full_skill(self, name: str, version: str = None) -> Optional[SkillSpec]:
        base = self.get_skill(name, version)
        if not base:
            return None
        if not base.source_path or not os.path.exists(base.source_path):
            return base
        with open(base.source_path, "r") as f:
            content = f.read()
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

# Global registry instance
skill_registry = SkillRegistry()

class LegacyAgentAdapter:
    @staticmethod
    def to_descriptor(agent: Any) -> RuntimeCapabilityDescriptor:
        # Import inside to avoid circular dependency
        from app.services.agent_store import AgentConfig
        if not isinstance(agent, AgentConfig):
            raise ValueError(f"Expected AgentConfig, got {type(agent)}")
            
        return RuntimeCapabilityDescriptor(
            prompt_blocks={"system_prompt": agent.system_prompt},
            tool_policy={"enabled_tools": agent.enabled_tools},
            constraints={},
            source_type="legacy_agent",
            name=agent.name,
            version="1.0.0"
        )

class MarkdownSkillAdapter:
    @staticmethod
    def to_descriptor(skill: SkillSpec) -> RuntimeCapabilityDescriptor:
        prompt_blocks = {}
        if skill.system_prompt:
            prompt_blocks["system_prompt"] = skill.system_prompt
        if skill.instructions:
            prompt_blocks["instructions"] = skill.instructions
        if skill.examples:
            prompt_blocks["examples"] = skill.examples
        if skill.failure_handling:
            prompt_blocks["failure_handling"] = skill.failure_handling
            
        return RuntimeCapabilityDescriptor(
            prompt_blocks=prompt_blocks,
            tool_policy={"allowed_tools": skill.constraints.allowed_tools if skill.constraints else None},
            constraints=skill.constraints.model_dump() if skill.constraints else {},
            source_type="markdown_skill",
            name=skill.name,
            version=skill.version
        )

class SkillRouter:
    """
    Agent-scoped skill filtering, ranking, and fallback.
    """
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def resolve_visible_skill_refs(self, agent: Any) -> List[str]:
        refs: List[str] = []
        pre_resolved_refs = getattr(agent, "resolved_visible_skills", None) or []
        refs.extend(pre_resolved_refs)
        selected_group_ids = getattr(agent, "skill_groups", None) or []
        if not pre_resolved_refs:
            refs.extend(skill_group_store.get_skill_refs_by_group_ids(selected_group_ids))
        extra_refs = getattr(agent, "extra_visible_skills", None) or []
        if not pre_resolved_refs:
            refs.extend(extra_refs)
        legacy_refs = getattr(agent, "visible_skills", None) or []
        if not pre_resolved_refs:
            refs.extend(legacy_refs)
        deduped: List[str] = []
        seen = set()
        for ref in refs:
            if not isinstance(ref, str):
                continue
            norm = ref.strip()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            deduped.append(norm)
        return deduped

    def get_visible_skills(self, agent: Any) -> List[SkillSpec]:
        """
        Filter skills based on agent.visible_skills allowlist.
        If agent.visible_skills is empty, no skills are visible (fail-closed).
        """
        visible_refs = self.resolve_visible_skill_refs(agent)
        if not visible_refs:
            return []
            
        visible = []
        for name_version in visible_refs:
            # name_version can be "name" or "name:version"
            if ":" in name_version:
                name, version = name_version.split(":", 1)
            else:
                name, version = name_version, None
                
            skill = self.registry.get_skill(name, version)
            if skill:
                visible.append(skill)
        return visible

    def _tokenize_ascii(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _tokenize_cjk(self, text: str) -> List[str]:
        return re.findall(r"[\u4e00-\u9fff]{2,}", text)

    def _score_skill(self, skill: SkillSpec, task_text: str, task_tokens: set, task_cjk: set) -> int:
        score = 0
        name = skill.name or ""
        description = skill.description or ""
        capabilities = skill.capabilities or []

        name_lower = name.lower()
        if name_lower and name_lower in task_text:
            score += 6

        name_tokens = set(self._tokenize_ascii(name))
        score += 3 * len(name_tokens.intersection(task_tokens))

        desc_tokens = set(self._tokenize_ascii(description))
        score += 1 * len(desc_tokens.intersection(task_tokens))

        desc_cjk = set(self._tokenize_cjk(description))
        score += 1 * len(desc_cjk.intersection(task_cjk))

        for cap in capabilities:
            cap_text = cap or ""
            cap_lower = cap_text.lower()
            if cap_lower and cap_lower in task_text:
                score += 5
            cap_tokens = set(self._tokenize_ascii(cap_text))
            score += 2 * len(cap_tokens.intersection(task_tokens))
            cap_cjk = set(self._tokenize_cjk(cap_text))
            score += 2 * len(cap_cjk.intersection(task_cjk))

        return score

    def score_skill(self, skill: SkillSpec, task: str) -> int:
        task_text = (task or "").lower()
        task_tokens = set(self._tokenize_ascii(task or ""))
        task_cjk = set(self._tokenize_cjk(task or ""))
        return self._score_skill(skill, task_text, task_tokens, task_cjk)

    def infer_requested_skill(self, agent: Any, task: str) -> Optional[str]:
        task_text = (task or "").strip().lower()
        if not task_text:
            return None
        visible_skills = self.get_visible_skills(agent)
        available_skills = [s for s in visible_skills if s.availability is not False]
        candidates: List[tuple[int, str]] = []
        for skill in available_skills:
            name = (skill.name or "").lower()
            if not name:
                continue
            name_version = f"{skill.name}:{skill.version}"
            if name_version.lower() in task_text:
                candidates.append((len(name_version), name_version))
                continue
            if name in task_text:
                candidates.append((len(name), name_version))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    def route_with_score(self, agent: Any, task: str, requested_skill: str = None) -> tuple[Optional[SkillSpec], int]:
        visible_skills = self.get_visible_skills(agent)
        available_skills = [s for s in visible_skills if s.availability is not False]
        if not visible_skills:
            return None, 0
        effective_requested_skill = requested_skill or self.infer_requested_skill(agent, task)
        if effective_requested_skill:
            if ":" in effective_requested_skill:
                req_name, req_version = effective_requested_skill.split(":", 1)
            else:
                req_name, req_version = effective_requested_skill, None
            for s in available_skills:
                if s.name == req_name and (not req_version or s.version == req_version):
                    return s, 1000
            return None, 0
        task_text = (task or "").lower()
        task_tokens = set(self._tokenize_ascii(task or ""))
        task_cjk = set(self._tokenize_cjk(task or ""))
        scored = [(self._score_skill(skill, task_text, task_tokens, task_cjk), skill) for skill in available_skills]
        scored.sort(key=lambda item: (-item[0], item[1].name))
        if scored and scored[0][0] > 0:
            return scored[0][1], scored[0][0]
        return None, 0

    def route(self, agent: Any, task: str, requested_skill: str = None) -> Optional[SkillSpec]:
        """
        Resolve the best skill for an agent and task.
        Tie-break order:
        1. Explicitly requested skill (if in visible_skills)
        2. higher capability match score (placeholder)
        3. lexical order of skill name as final deterministic tie-breaker
        """
        skill, _score = self.route_with_score(agent, task, requested_skill=requested_skill)
        return skill

class SkillPolicyGate:
    """
    Authorization checks for selection and runtime binding.
    """
    @staticmethod
    def check_tool_intersection(agent_tools: List[str], skill_allowed_tools: Optional[List[str]]) -> List[str]:
        """
        Enforce: final_tools = agent.enabled_tools ∩ skill.allowed_tools
        If skill.allowed_tools is None, it means the skill doesn't restrict tools.
        """
        if skill_allowed_tools is None:
            return agent_tools
            
        # Set intersection
        agent_set = set(agent_tools)
        skill_set = set(skill_allowed_tools)
        return list(agent_set.intersection(skill_set))

# Global router instance
skill_router = SkillRouter(skill_registry)
