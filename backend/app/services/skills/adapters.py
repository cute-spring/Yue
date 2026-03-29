from typing import Any

from app.services.skills.models import RuntimeCapabilityDescriptor, RuntimeSkillActionDescriptor, SkillSpec


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
    def to_action_descriptors(skill: SkillSpec) -> list[RuntimeSkillActionDescriptor]:
        metadata = skill.metadata or {}
        raw_actions = metadata.get("package_actions")
        if not isinstance(raw_actions, list):
            return []

        actions: list[RuntimeSkillActionDescriptor] = []
        for raw_action in raw_actions:
            if not isinstance(raw_action, dict):
                continue
            action_id = raw_action.get("id")
            if not action_id:
                continue
            actions.append(
                RuntimeSkillActionDescriptor(
                    id=str(action_id),
                    name=skill.name,
                    version=skill.version,
                    tool=raw_action.get("tool"),
                    resource=raw_action.get("resource"),
                    path=raw_action.get("path"),
                    runtime=raw_action.get("runtime"),
                    load_tier=str(raw_action.get("load_tier") or "action"),
                    safety=raw_action.get("safety"),
                    approval_policy=raw_action.get("approval_policy"),
                    input_schema=raw_action.get("input_schema") if isinstance(raw_action.get("input_schema"), dict) else {},
                    output_schema=raw_action.get("output_schema") if isinstance(raw_action.get("output_schema"), dict) else {},
                    metadata=raw_action.get("metadata") if isinstance(raw_action.get("metadata"), dict) else {},
                )
            )
        return actions

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
            actions=MarkdownSkillAdapter.to_action_descriptors(skill),
            source_type="markdown_skill",
            name=skill.name,
            version=skill.version,
        )
