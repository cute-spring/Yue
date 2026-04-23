from dataclasses import dataclass
from typing import Any, Callable, List

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
    SkillRuntimeSeams,
    refresh_runtime_registry_for_import_gate,
    resolve_skill_runtime_mode,
    build_skill_runtime_seams,
    build_action_execution_result_event,
    build_action_invocation_event,
)
from app.services.skills.routing import SkillRouter as ExtractedSkillRouter

def refresh_skill_runtime_catalog() -> bool:
    runtime_registry, runtime_import_store = _resolve_runtime_catalog_dependencies()
    return refresh_runtime_registry_for_import_gate(
        skill_registry=runtime_registry,
        import_store=runtime_import_store,
        runtime_mode=resolve_skill_runtime_mode(),
    )


def build_stage4_lite_runtime_seams(
    *,
    import_store: SkillImportStore | None = None,
    router: Any | None = None,
) -> SkillRuntimeSeams:
    if import_store is None or router is None:
        context = get_stage4_lite_runtime_context()
        if import_store is None:
            import_store = context.skill_import_store
        if router is None:
            router = context.skill_router
    return build_skill_runtime_seams(
        import_store=import_store,
        router=router,
    )


class SkillRouter(ExtractedSkillRouter):
    """
    Compatibility wrapper that preserves the historical patch seam at
    app.services.skill_service.skill_group_store.
    """

    def __init__(self, registry: Any, skill_group_store: Any = None, visibility_resolver: Any = None):
        super().__init__(
            registry,
            skill_group_store=skill_group_store or globals()["skill_group_store"],
            visibility_resolver=visibility_resolver,
        )
        self.skill_group_store = skill_group_store

    def resolve_visible_skill_refs(self, agent: Any) -> List[str]:
        group_store = self.skill_group_store or skill_group_store
        original_group_store = self.skill_group_store
        self.skill_group_store = group_store
        try:
            return super().resolve_visible_skill_refs(agent)
        finally:
            self.skill_group_store = original_group_store

@dataclass(frozen=True)
class _Stage4LiteRuntimeSingletons:
    skill_registry: SkillRegistry
    skill_router: SkillRouter
    skill_action_execution_service: SkillActionExecutionService
    skill_import_store: SkillImportStore
    skill_compatibility_evaluator: SkillCompatibilityEvaluator
    skill_import_service: SkillImportService


def _build_stage4_lite_runtime_singletons() -> _Stage4LiteRuntimeSingletons:
    registry = SkillRegistry()
    router = SkillRouter(registry)
    action_execution_service = SkillActionExecutionService(registry)
    import_store = SkillImportStore()
    compatibility_evaluator = SkillCompatibilityEvaluator()
    import_service = SkillImportService(
        import_store=import_store,
        compatibility_evaluator=compatibility_evaluator,
    )
    return _Stage4LiteRuntimeSingletons(
        skill_registry=registry,
        skill_router=router,
        skill_action_execution_service=action_execution_service,
        skill_import_store=import_store,
        skill_compatibility_evaluator=compatibility_evaluator,
        skill_import_service=import_service,
    )


_stage4_lite_runtime_singletons = _build_stage4_lite_runtime_singletons()

# Backward compatibility shim for historical module-level patch seams/imports.
skill_registry = _stage4_lite_runtime_singletons.skill_registry
skill_router = _stage4_lite_runtime_singletons.skill_router
skill_action_execution_service = _stage4_lite_runtime_singletons.skill_action_execution_service
skill_import_store = _stage4_lite_runtime_singletons.skill_import_store
skill_compatibility_evaluator = _stage4_lite_runtime_singletons.skill_compatibility_evaluator
skill_import_service = _stage4_lite_runtime_singletons.skill_import_service


@dataclass(frozen=True)
class Stage4LiteRuntimeProviders:
    registry: Callable[[], Any]
    router: Callable[[], Any]
    action_execution_service: Callable[[], Any]
    import_store: Callable[[], Any]
    import_service: Callable[[], Any]


def _default_stage4_lite_runtime_providers() -> Stage4LiteRuntimeProviders:
    return Stage4LiteRuntimeProviders(
        registry=lambda: _stage4_lite_runtime_singletons.skill_registry,
        router=lambda: _stage4_lite_runtime_singletons.skill_router,
        action_execution_service=lambda: _stage4_lite_runtime_singletons.skill_action_execution_service,
        import_store=lambda: _stage4_lite_runtime_singletons.skill_import_store,
        import_service=lambda: _stage4_lite_runtime_singletons.skill_import_service,
    )


_stage4_lite_runtime_providers = _default_stage4_lite_runtime_providers()
_stage4_lite_runtime_providers_overridden = False


def set_stage4_lite_runtime_providers(providers: Stage4LiteRuntimeProviders | None) -> None:
    global _stage4_lite_runtime_providers
    global _stage4_lite_runtime_providers_overridden
    _stage4_lite_runtime_providers = providers or _default_stage4_lite_runtime_providers()
    _stage4_lite_runtime_providers_overridden = providers is not None


def reset_stage4_lite_runtime_providers() -> None:
    global _stage4_lite_runtime_providers
    global _stage4_lite_runtime_providers_overridden
    _stage4_lite_runtime_providers = _default_stage4_lite_runtime_providers()
    _stage4_lite_runtime_providers_overridden = False


def get_stage4_lite_runtime_providers() -> Stage4LiteRuntimeProviders:
    return _stage4_lite_runtime_providers


@dataclass(frozen=True)
class Stage4LiteRuntimeContext:
    skill_registry: SkillRegistry
    skill_router: SkillRouter
    skill_action_execution_service: SkillActionExecutionService
    skill_import_store: SkillImportStore
    skill_import_service: SkillImportService


def _default_stage4_lite_runtime_context_factory() -> Stage4LiteRuntimeContext:
    providers = get_stage4_lite_runtime_providers()
    return Stage4LiteRuntimeContext(
        skill_registry=providers.registry(),
        skill_router=providers.router(),
        skill_action_execution_service=providers.action_execution_service(),
        skill_import_store=providers.import_store(),
        skill_import_service=providers.import_service(),
    )


_stage4_lite_runtime_context_factory = _default_stage4_lite_runtime_context_factory


def set_stage4_lite_runtime_context_factory(factory: Any) -> None:
    global _stage4_lite_runtime_context_factory
    _stage4_lite_runtime_context_factory = factory or _default_stage4_lite_runtime_context_factory


def reset_stage4_lite_runtime_context_factory() -> None:
    global _stage4_lite_runtime_context_factory
    _stage4_lite_runtime_context_factory = _default_stage4_lite_runtime_context_factory


def get_stage4_lite_runtime_context() -> Stage4LiteRuntimeContext:
    context = _stage4_lite_runtime_context_factory()
    return context


def _resolve_runtime_catalog_dependencies() -> tuple[Any, Any]:
    # Compatibility shim: historical tests and call-sites monkeypatch module aliases
    # directly. Keep that seam for default runtime providers.
    if not _stage4_lite_runtime_providers_overridden:
        return skill_registry, skill_import_store
    context = get_stage4_lite_runtime_context()
    return context.skill_registry, context.skill_import_store


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
    "Stage4LiteRuntimeContext",
    "Stage4LiteRuntimeProviders",
    "SkillRuntimeSeams",
    "get_stage4_lite_runtime_context",
    "get_stage4_lite_runtime_providers",
    "set_stage4_lite_runtime_context_factory",
    "set_stage4_lite_runtime_providers",
    "reset_stage4_lite_runtime_context_factory",
    "reset_stage4_lite_runtime_providers",
    "refresh_runtime_registry_for_import_gate",
    "refresh_skill_runtime_catalog",
    "resolve_skill_runtime_mode",
    "build_stage4_lite_runtime_seams",
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
