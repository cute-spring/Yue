import os
import yaml
import logging
import re
import platform
import shutil
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

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

class SkillSummary(BaseModel):
    name: str
    description: str
    availability: Optional[bool] = True
    source_path: Optional[str] = None

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
            
        return SkillValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

class SkillRegistry:
    """
    In-memory skill index keyed by (name, version).
    """
    def __init__(self, skill_dirs: List[str] = None):
        self.skill_dirs = skill_dirs or []
        self._skills: Dict[str, Dict[str, SkillSpec]] = {} # name -> {version -> spec}
        self._latest_versions: Dict[str, str] = {} # name -> latest_version

    def load_all(self):
        self._skills = {}
        self._latest_versions = {}
        
        for skill_dir in self.skill_dirs:
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
                    source_path=skill.source_path
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
            tool_policy={"allowed_tools": skill.constraints.allowed_tools if skill.constraints else []},
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

    def get_visible_skills(self, agent: Any) -> List[SkillSpec]:
        """
        Filter skills based on agent.visible_skills allowlist.
        If agent.visible_skills is empty, no skills are visible (fail-closed).
        """
        if not hasattr(agent, "visible_skills") or not agent.visible_skills:
            return []
            
        visible = []
        for name_version in agent.visible_skills:
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
