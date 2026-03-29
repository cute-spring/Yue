"""
Kernel-facing facade for Yue's skill system.

This package should preferentially export host-neutral contracts, models,
parsing/registry helpers, and reusable runtime helpers. Yue-specific runtime
composition and persistence-backed adapters should stay outside this facade and
be wired in higher-level modules such as `app.services.skill_service`.
"""

from app.services.skills.actions import (
    SkillActionExecutionService,
)
from app.services.skills.browser_continuity_contracts import (
    BrowserContinuityLookupBackend,
    BrowserContinuityResolver,
    DefaultBrowserContinuityLookupBackend,
    DefaultBrowserContinuityResolver,
    ExplicitContextBrowserContinuityResolver,
)
from app.services.skills.runtime_contracts import (
    build_action_approval_event,
    build_action_approval_message,
    build_action_execution_transition_event,
    build_action_execution_stub_message,
    build_action_preflight_message,
    build_action_execution_result_event,
    build_action_invocation_event,
)
from app.services.skills.adapters import LegacyAgentAdapter, MarkdownSkillAdapter
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
from app.services.skills.routing import SkillRouter

__all__ = [
    # Skill package and runtime models
    # Keep these stable for future kernel extraction.
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
    "SkillActionSpec",
    "SkillConstraints",
    "SkillDirectorySpec",
    "SkillLoadingPolicy",
    "SkillOverlaySpec",
    "SkillPackageSpec",
    "SkillReferenceSpec",
    "SkillResourceSpec",
    "SkillScriptSpec",
    "SkillSpec",
    "SkillSummary",
    "SkillValidationResult",
    # Loading, parsing, registry, routing
    "LegacyAgentAdapter",
    "MarkdownSkillAdapter",
    "SKILL_LAYER_PRIORITY",
    "SkillDirectoryResolver",
    "SkillLoader",
    "SkillPolicyGate",
    "SkillRegistry",
    "SkillRouter",
    "SkillValidator",
    # Reusable continuity/runtime contracts
    "BrowserContinuityLookupBackend",
    "BrowserContinuityResolver",
    "DefaultBrowserContinuityLookupBackend",
    "DefaultBrowserContinuityResolver",
    "ExplicitContextBrowserContinuityResolver",
    "SkillActionExecutionService",
    "build_action_execution_result_event",
    "build_action_execution_transition_event",
    "build_action_invocation_event",
    "build_action_approval_event",
    "build_action_preflight_message",
    "build_action_approval_message",
    "build_action_execution_stub_message",
]
