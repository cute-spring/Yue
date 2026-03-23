from typing import Any, List

from app.services.skill_group_store import skill_group_store
from app.services.skills import (
    LegacyAgentAdapter,
    MarkdownSkillAdapter,
    RuntimeCapabilityDescriptor,
    SKILL_LAYER_PRIORITY,
    SkillConstraints,
    SkillDirectoryResolver,
    SkillDirectorySpec,
    SkillLoader,
    SkillPolicyGate,
    SkillRegistry,
    SkillSpec,
    SkillSummary,
    SkillValidationResult,
    SkillValidator,
)
from app.services.skills.routing import SkillRouter as ExtractedSkillRouter

# Global registry instance
skill_registry = SkillRegistry()


class SkillRouter(ExtractedSkillRouter):
    """
    Compatibility wrapper that preserves the historical patch seam at
    app.services.skill_service.skill_group_store.
    """

    def __init__(self, registry: Any, skill_group_store: Any = None):
        super().__init__(registry, skill_group_store=skill_group_store or globals()["skill_group_store"])
        self.skill_group_store = skill_group_store

    def resolve_visible_skill_refs(self, agent: Any) -> List[str]:
        group_store = self.skill_group_store or skill_group_store
        original_group_store = self.skill_group_store
        self.skill_group_store = group_store
        try:
            return super().resolve_visible_skill_refs(agent)
        finally:
            self.skill_group_store = original_group_store

# Global router instance
skill_router = SkillRouter(skill_registry)

__all__ = [
    "LegacyAgentAdapter",
    "MarkdownSkillAdapter",
    "RuntimeCapabilityDescriptor",
    "SKILL_LAYER_PRIORITY",
    "SkillConstraints",
    "SkillDirectoryResolver",
    "SkillDirectorySpec",
    "SkillLoader",
    "SkillPolicyGate",
    "SkillRegistry",
    "SkillRouter",
    "SkillSpec",
    "SkillSummary",
    "SkillValidationResult",
    "SkillValidator",
    "skill_group_store",
    "skill_registry",
    "skill_router",
]
