from typing import Any, List

from app.services.browser_continuity import YueActionStateBrowserContinuityLookupBackend
from app.services.chat_service import chat_service
from app.services.skill_group_store import skill_group_store
from app.services.skills.actions import SkillActionExecutionService
from app.services.skills.adapters import LegacyAgentAdapter, MarkdownSkillAdapter
from app.services.skills.browser_continuity_contracts import (
    BrowserContinuityLookupBackend,
    BrowserContinuityResolver,
    DefaultBrowserContinuityLookupBackend,
    DefaultBrowserContinuityResolver,
    ExplicitContextBrowserContinuityResolver,
)
from app.services.skills.directories import SKILL_LAYER_PRIORITY, SkillDirectoryResolver
from app.services.skills.models import (
    RuntimeBrowserContinuityLookupRequest,
    RuntimeBrowserContinuityLookupResult,
    RuntimeBrowserContinuityResolutionRequest,
    RuntimeBrowserContinuityResolutionResult,
    RuntimeCapabilityDescriptor,
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionApprovalResult,
    RuntimeSkillActionDescriptor,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionExecutionResult,
    RuntimeSkillActionInvocationRequest,
    RuntimeSkillActionInvocationResult,
    SkillActionSpec,
    SkillConstraints,
    SkillDirectorySpec,
    SkillLoadingPolicy,
    SkillOverlaySpec,
    SkillPackageSpec,
    SkillReferenceSpec,
    SkillResourceSpec,
    SkillScriptSpec,
    SkillSpec,
    SkillSummary,
    SkillValidationResult,
)
from app.services.skills.parsing import SkillLoader, SkillValidator
from app.services.skills.policy import SkillPolicyGate
from app.services.skills.registry import SkillRegistry
from app.services.skills.runtime_contracts import (
    build_action_approval_event,
    build_action_approval_message,
    build_action_execution_result_event,
    build_action_execution_stub_message,
    build_action_execution_transition_event,
    build_action_invocation_event,
)
from app.services.skills.routing import SkillRouter as ExtractedSkillRouter

# Global registry instance
skill_registry = SkillRegistry()
skill_action_execution_service = SkillActionExecutionService(
    skill_registry,
    continuity_resolver=ExplicitContextBrowserContinuityResolver(
        lookup_backend=YueActionStateBrowserContinuityLookupBackend(chat_service=chat_service)
    ),
)


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
    "BrowserContinuityLookupBackend",
    "BrowserContinuityResolver",
    "DefaultBrowserContinuityLookupBackend",
    "DefaultBrowserContinuityResolver",
    "ExplicitContextBrowserContinuityResolver",
    "SkillActionExecutionService",
    "build_action_approval_event",
    "build_action_approval_message",
    "build_action_execution_transition_event",
    "build_action_execution_stub_message",
    "build_action_preflight_message",
    "RuntimeBrowserContinuityLookupRequest",
    "RuntimeBrowserContinuityLookupResult",
    "RuntimeBrowserContinuityResolutionRequest",
    "RuntimeBrowserContinuityResolutionResult",
    "RuntimeCapabilityDescriptor",
    "RuntimeSkillActionApprovalRequest",
    "RuntimeSkillActionApprovalResult",
    "RuntimeSkillActionDescriptor",
    "RuntimeSkillActionExecutionRequest",
    "RuntimeSkillActionExecutionResult",
    "RuntimeSkillActionInvocationRequest",
    "RuntimeSkillActionInvocationResult",
    "SKILL_LAYER_PRIORITY",
    "SkillActionSpec",
    "SkillConstraints",
    "SkillDirectoryResolver",
    "SkillDirectorySpec",
    "SkillLoader",
    "SkillLoadingPolicy",
    "SkillOverlaySpec",
    "SkillPackageSpec",
    "SkillPolicyGate",
    "SkillReferenceSpec",
    "SkillRegistry",
    "SkillRouter",
    "SkillResourceSpec",
    "SkillScriptSpec",
    "SkillSpec",
    "SkillSummary",
    "SkillValidationResult",
    "SkillValidator",
    "YueActionStateBrowserContinuityLookupBackend",
    "build_action_execution_result_event",
    "build_action_invocation_event",
    "skill_group_store",
    "skill_action_execution_service",
    "skill_registry",
    "skill_router",
]
