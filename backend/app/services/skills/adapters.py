from typing import Any

from app.services.skills.models import RuntimeCapabilityDescriptor, SkillSpec


class LegacyAgentAdapter:
    @staticmethod
    def to_descriptor(agent: Any) -> RuntimeCapabilityDescriptor:
        from app.services.agent_store import AgentConfig

        if not isinstance(agent, AgentConfig):
            raise ValueError(f"Expected AgentConfig, got {type(agent)}")

        return RuntimeCapabilityDescriptor(
            prompt_blocks={"system_prompt": agent.system_prompt},
            tool_policy={"enabled_tools": agent.enabled_tools},
            constraints={},
            source_type="legacy_agent",
            name=agent.name,
            version="1.0.0",
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
            version=skill.version,
        )
