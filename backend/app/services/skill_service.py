from typing import Any, List

from app.services.skill_group_store import skill_group_store
from app.services.skills import (
    LegacyAgentAdapter,
    MarkdownSkillAdapter,
    SkillActionExecutionService,
    build_action_approval_event,
    build_action_approval_message,
    build_action_execution_transition_event,
    build_action_execution_stub_message,
    build_action_preflight_message,
    RuntimeCapabilityDescriptor,
    SkillCompatibilityEvaluator,
    SkillImportLifecycleState,
    SkillImportPreview,
    SkillImportRecord,
    SkillImportReport,
    SkillImportResult,
    SkillImportService,
    SkillImportSource,
    SkillImportSourceType,
    SkillImportStore,
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionApprovalResult,
    RuntimeSkillActionDescriptor,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionExecutionResult,
    RuntimeSkillActionInvocationRequest,
    RuntimeSkillActionInvocationResult,
    SKILL_LAYER_PRIORITY,
    SkillActionSpec,
    SkillConstraints,
    SkillDirectoryResolver,
    SkillDirectorySpec,
    SkillLoader,
    SkillLoadingPolicy,
    SkillOverlaySpec,
    SkillPackageSpec,
    SkillPolicyGate,
    SkillReferenceSpec,
    SkillRegistry,
    SkillResourceSpec,
    SkillScriptSpec,
    SkillSpec,
    SkillSummary,
    SkillValidationResult,
    SkillValidator,
    RUNTIME_MODE_ENV_KEY,
    RUNTIME_MODE_IMPORT_GATE,
    RUNTIME_MODE_LEGACY,
    RuntimeSkillCatalogProjector,
    refresh_runtime_registry_for_import_gate,
    resolve_skill_runtime_mode,
    build_action_execution_result_event,
    build_action_invocation_event,
)
from app.services.skills.routing import SkillRouter as ExtractedSkillRouter

# Global registry instance
skill_registry = SkillRegistry()
skill_action_execution_service = SkillActionExecutionService(skill_registry)
skill_import_store = SkillImportStore()
skill_compatibility_evaluator = SkillCompatibilityEvaluator()
skill_import_service = SkillImportService(
    import_store=skill_import_store,
    compatibility_evaluator=skill_compatibility_evaluator,
)


def refresh_skill_runtime_catalog() -> bool:
    return refresh_runtime_registry_for_import_gate(
        skill_registry=skill_registry,
        import_store=skill_import_store,
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
    "SkillCompatibilityEvaluator",
    "SkillImportLifecycleState",
    "SkillImportPreview",
    "SkillImportRecord",
    "SkillImportReport",
    "SkillImportResult",
    "SkillImportService",
    "SkillImportSource",
    "SkillImportSourceType",
    "SkillImportStore",
    "SkillActionExecutionService",
    "build_action_approval_event",
    "build_action_approval_message",
    "build_action_execution_transition_event",
    "build_action_execution_stub_message",
    "build_action_preflight_message",
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
    "RUNTIME_MODE_ENV_KEY",
    "RUNTIME_MODE_IMPORT_GATE",
    "RUNTIME_MODE_LEGACY",
    "RuntimeSkillCatalogProjector",
    "refresh_runtime_registry_for_import_gate",
    "refresh_skill_runtime_catalog",
    "resolve_skill_runtime_mode",
    "build_action_execution_result_event",
    "build_action_invocation_event",
    "skill_group_store",
    "skill_action_execution_service",
    "skill_compatibility_evaluator",
    "skill_import_service",
    "skill_import_store",
    "skill_registry",
    "skill_router",
]
