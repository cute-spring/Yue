import os
import yaml
import logging
import re
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
    
    # Sections parsed from Markdown
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    examples: Optional[str] = None
    failure_handling: Optional[str] = None
    
    # Metadata
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
            
            for root, _, files in os.walk(skill_dir):
                for file in files:
                    if file.endswith(".md"):
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

    def route(self, agent: Any, task: str, requested_skill: str = None) -> Optional[SkillSpec]:
        """
        Resolve the best skill for an agent and task.
        Tie-break order:
        1. Explicitly requested skill (if in visible_skills)
        2. higher capability match score (placeholder)
        3. lexical order of skill name as final deterministic tie-breaker
        """
        visible_skills = self.get_visible_skills(agent)
        if not visible_skills:
            return None
            
        # 1. Check explicitly requested skill
        if requested_skill:
            if ":" in requested_skill:
                req_name, req_version = requested_skill.split(":", 1)
            else:
                req_name, req_version = requested_skill, None
                
            for s in visible_skills:
                if s.name == req_name and (not req_version or s.version == req_version):
                    return s
        
        # 2. Ranking logic (Phase B simple version: just use lexical order for now)
        # In a real scenario, we'd use LLM or keyword matching against 'capabilities'
        sorted_skills = sorted(visible_skills, key=lambda s: s.name)
        if sorted_skills:
            return sorted_skills[0]
            
        return None

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
