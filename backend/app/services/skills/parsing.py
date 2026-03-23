import logging
import re
from typing import Any, List, Optional

import yaml

from app.services.skills.models import SkillSpec, SkillValidationResult


logger = logging.getLogger(__name__)


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v is not None and str(v).strip()]
    if isinstance(value, str):
        val = value.strip()
        return [val] if val else []
    return []


class SkillLoader:
    """
    Discovery, parse, and normalize skills from Markdown files.
    """

    @staticmethod
    def parse_markdown(content: str, source_path: str = None) -> Optional[SkillSpec]:
        try:
            parts = re.split(r"^---\s*$", content, flags=re.MULTILINE)
            if len(parts) < 3:
                logger.error("Invalid skill format in %s: missing frontmatter delimiters", source_path)
                return None

            frontmatter_raw = parts[1].strip()
            markdown_content = "---".join(parts[2:]).strip()

            frontmatter = yaml.safe_load(frontmatter_raw)
            if not isinstance(frontmatter, dict):
                logger.error("Invalid frontmatter in %s", source_path)
                return None

            raw_requires = frontmatter.get("requires")
            requires = None
            if isinstance(raw_requires, dict):
                bins = _normalize_list(raw_requires.get("bins") or raw_requires.get("bin"))
                env = _normalize_list(raw_requires.get("env"))
                requires = {"bins": bins, "env": env}
            elif isinstance(raw_requires, list) or isinstance(raw_requires, str):
                requires = {"bins": _normalize_list(raw_requires), "env": []}

            raw_os = frontmatter.get("os")
            os_list = _normalize_list(raw_os)
            os_list = [o.lower() for o in os_list] if os_list else None

            metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else None
            install = frontmatter.get("install") if isinstance(frontmatter.get("install"), dict) else None

            sections = {}
            current_section = None
            section_content = []

            for line in markdown_content.splitlines():
                match = re.match(r"^##\s+(.+)$", line)
                if match:
                    if current_section:
                        sections[current_section] = "\n".join(section_content).strip()
                    current_section = match.group(1).strip().lower().replace(" ", "_")
                    section_content = []
                elif current_section:
                    section_content.append(line)

            if current_section:
                sections[current_section] = "\n".join(section_content).strip()

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
        except Exception as exc:
            logger.exception("Error parsing skill in %s: %s", source_path, exc)
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

        entrypoint_attr = skill.entrypoint.lower().replace(" ", "_")
        if not getattr(skill, entrypoint_attr, None):
            errors.append(f"Entrypoint section '{skill.entrypoint}' not found in Markdown")

        if skill.system_prompt and len(skill.system_prompt.strip()) < 10:
            warnings.append("System prompt is very short")

        if skill.inputs_schema is not None and not isinstance(skill.inputs_schema, dict):
            errors.append("inputs_schema must be a dictionary")
        if skill.outputs_schema is not None and not isinstance(skill.outputs_schema, dict):
            errors.append("outputs_schema must be a dictionary")

        if skill.constraints and skill.constraints.allowed_tools is not None:
            if not isinstance(skill.constraints.allowed_tools, list):
                errors.append("constraints.allowed_tools must be a list")
            else:
                for tool in skill.constraints.allowed_tools:
                    if not isinstance(tool, str):
                        errors.append(f"Invalid tool name in allowed_tools: {tool}")

        return SkillValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
