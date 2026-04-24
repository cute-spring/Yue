from dataclasses import dataclass
from typing import Any, Callable, List

from app.services.skill_group_store import skill_group_store
from app.services.skills import (
    AgentProvider,
    BuiltSkillRuntime,
    ConfigFeatureFlagProvider,
    FeatureFlagProvider,
    GroupAwareAgentVisibilityResolver,
    GroupStoreSkillGroupResolver,
    HostConfigAdapter,
    HostRuntimeAdapterBundle,
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
    SkillRuntimeConfig,
    SkillGroupResolver,
    SkillValidationResult,
    SkillValidator,
    StoreBackedAgentProvider,
    build_default_host_runtime_adapter_bundle,
    build_skill_runtime,
    RUNTIME_MODE_ENV_KEY,
    RUNTIME_MODE_IMPORT_GATE,
    RUNTIME_MODE_LEGACY,
    RuntimeSkillCatalogProjector,
    SkillRuntimeSeams,
    refresh_runtime_registry_for_import_gate,
    resolve_skill_runtime_config_from_env,
    resolve_skill_runtime_mode,
    build_skill_runtime_seams,
    build_action_execution_result_event,
    build_action_invocation_event,
)
from app.services.skills.routing import SkillRouter as ExtractedSkillRouter

# Transitional compatibility shell. This module remains copy-first reusable for
# same-stack hosts, but it is not part of the future pure runtime core package.

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
    # Transitional facade: prefer the runtime context path, while preserving the
    # historical escape hatch for callers that still pass concrete dependencies.
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
        resolver = visibility_resolver or GroupAwareAgentVisibilityResolver(
            skill_group_resolver=skill_group_store or globals()["skill_group_store"],
        )
        super().__init__(
            registry,
            visibility_resolver=resolver,
        )
        # Preserve the historical patch seam where tests patch
        # app.services.skill_service.skill_group_store after router construction.
        self._compat_skill_group_store_override = skill_group_store
        self.skill_group_store = skill_group_store

    def resolve_visible_skill_refs(self, agent: Any) -> List[str]:
        original_override = self._compat_skill_group_store_override
        group_store = original_override
        if group_store is None:
            group_store = self.skill_group_store or skill_group_store
        self.skill_group_store = group_store
        try:
            return super().resolve_visible_skill_refs(agent)
        finally:
            self.skill_group_store = original_override or group_store

@dataclass(frozen=True)
class _Stage4LiteRuntimeSingletons:
    skill_registry: SkillRegistry
    skill_router: SkillRouter
    skill_action_execution_service: SkillActionExecutionService
    skill_import_store: SkillImportStore
    skill_compatibility_evaluator: SkillCompatibilityEvaluator
    skill_import_service: SkillImportService


def _build_stage4_lite_runtime_singletons() -> _Stage4LiteRuntimeSingletons:
    # Compatibility singleton holder. The singleton still exists for Yue and old
    # tests, but the construction path now goes through the public builder.
    runtime = build_skill_runtime(
        config=resolve_skill_runtime_config_from_env(),
        router_factory=lambda registry: SkillRouter(registry),
        action_service_factory=lambda registry: SkillActionExecutionService(registry),
    )
    return _Stage4LiteRuntimeSingletons(
        skill_registry=runtime.skill_registry,
        skill_router=runtime.skill_router,
        skill_action_execution_service=runtime.skill_action_execution_service,
        skill_import_store=runtime.skill_import_store,
        skill_compatibility_evaluator=runtime.skill_compatibility_evaluator,
        skill_import_service=runtime.skill_import_service,
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


@dataclass(frozen=True)
class Stage4LiteHostAdapters:
    agent_provider: AgentProvider
    feature_flag_provider: FeatureFlagProvider
    skill_group_resolver: SkillGroupResolver
    visibility_resolver: Any | None = None


def _build_stage4_lite_visibility_resolver(skill_group_resolver: SkillGroupResolver | None) -> Any:
    return GroupAwareAgentVisibilityResolver(skill_group_resolver=skill_group_resolver)


def _default_stage4_lite_runtime_providers() -> Stage4LiteRuntimeProviders:
    return Stage4LiteRuntimeProviders(
        registry=lambda: _stage4_lite_runtime_singletons.skill_registry,
        router=lambda: _stage4_lite_runtime_singletons.skill_router,
        action_execution_service=lambda: _stage4_lite_runtime_singletons.skill_action_execution_service,
        import_store=lambda: _stage4_lite_runtime_singletons.skill_import_store,
        import_service=lambda: _stage4_lite_runtime_singletons.skill_import_service,
    )


_stage4_lite_runtime_providers = _default_stage4_lite_runtime_providers()


def _default_stage4_lite_host_adapters() -> Stage4LiteHostAdapters:
    from app.services.agent_store import agent_store
    from app.services.config_service import config_service

    return Stage4LiteHostAdapters(
        agent_provider=StoreBackedAgentProvider(agent_store),
        feature_flag_provider=ConfigFeatureFlagProvider(config_service),
        skill_group_resolver=GroupStoreSkillGroupResolver(skill_group_store),
        visibility_resolver=_build_stage4_lite_visibility_resolver(GroupStoreSkillGroupResolver(skill_group_store)),
    )


_stage4_lite_host_adapters = _default_stage4_lite_host_adapters()
skill_router.visibility_resolver = (
    _stage4_lite_host_adapters.visibility_resolver
    or _build_stage4_lite_visibility_resolver(_stage4_lite_host_adapters.skill_group_resolver)
)
_stage4_lite_host_config_adapter: HostConfigAdapter | None = None


def set_stage4_lite_runtime_providers(providers: Stage4LiteRuntimeProviders | None) -> None:
    global _stage4_lite_runtime_providers
    _stage4_lite_runtime_providers = providers or _default_stage4_lite_runtime_providers()


def reset_stage4_lite_runtime_providers() -> None:
    global _stage4_lite_runtime_providers
    _stage4_lite_runtime_providers = _default_stage4_lite_runtime_providers()


def get_stage4_lite_runtime_providers() -> Stage4LiteRuntimeProviders:
    return _stage4_lite_runtime_providers


def set_stage4_lite_host_adapters(adapters: Stage4LiteHostAdapters | None) -> None:
    global _stage4_lite_host_adapters
    resolved = adapters or _default_stage4_lite_host_adapters()
    _stage4_lite_host_adapters = resolved
    # Keep the default singleton router aligned with host visibility semantics.
    skill_router.visibility_resolver = resolved.visibility_resolver or _build_stage4_lite_visibility_resolver(
        resolved.skill_group_resolver
    )


def reset_stage4_lite_host_adapters() -> None:
    global _stage4_lite_host_adapters
    _stage4_lite_host_adapters = _default_stage4_lite_host_adapters()
    skill_router.visibility_resolver = (
        _stage4_lite_host_adapters.visibility_resolver
        or _build_stage4_lite_visibility_resolver(_stage4_lite_host_adapters.skill_group_resolver)
    )


def get_stage4_lite_host_adapters() -> Stage4LiteHostAdapters:
    return _stage4_lite_host_adapters


def set_stage4_lite_host_config_adapter(adapter: HostConfigAdapter | None) -> None:
    global _stage4_lite_host_config_adapter
    _stage4_lite_host_config_adapter = adapter


def reset_stage4_lite_host_config_adapter() -> None:
    global _stage4_lite_host_config_adapter
    _stage4_lite_host_config_adapter = None


def get_stage4_lite_host_config_adapter() -> HostConfigAdapter | None:
    return _stage4_lite_host_config_adapter


def register_stage4_lite_host_runtime_adapter_bundle(
    bundle: HostRuntimeAdapterBundle | None,
) -> HostRuntimeAdapterBundle:
    # Transitional host-wiring seam. Startup should register adapters here while
    # pure core extraction continues moving host ownership outward.
    if bundle is None:
        from app.services.agent_store import agent_store
        from app.services.config_service import config_service

        bundle = build_default_host_runtime_adapter_bundle(
            agent_store=agent_store,
            config_service=config_service,
            skill_group_store=skill_group_store,
        )
    set_stage4_lite_host_adapters(
        Stage4LiteHostAdapters(
            agent_provider=bundle.agent_provider,
            feature_flag_provider=bundle.feature_flag_provider,
            skill_group_resolver=bundle.skill_group_resolver,
            visibility_resolver=bundle.visibility_resolver,
        )
    )
    set_stage4_lite_host_config_adapter(bundle.host_config_provider)
    return bundle


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
    # Primary read path for API/startup callers. Reach the runtime through the
    # context factory/providers before falling back to module-level aliases.
    context = _stage4_lite_runtime_context_factory()
    return context


def _resolve_runtime_catalog_dependencies() -> tuple[Any, Any]:
    if (
        skill_registry is not _stage4_lite_runtime_singletons.skill_registry
        or skill_import_store is not _stage4_lite_runtime_singletons.skill_import_store
    ):
        # Backward-compatible patch seam for tests and legacy monkeypatch callers.
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
    "Stage4LiteHostAdapters",
    "Stage4LiteRuntimeProviders",
    "SkillRuntimeSeams",
    "SkillRuntimeConfig",
    "get_stage4_lite_runtime_context",
    "get_stage4_lite_host_config_adapter",
    "get_stage4_lite_host_adapters",
    "get_stage4_lite_runtime_providers",
    "register_stage4_lite_host_runtime_adapter_bundle",
    "set_stage4_lite_runtime_context_factory",
    "set_stage4_lite_host_config_adapter",
    "set_stage4_lite_host_adapters",
    "set_stage4_lite_runtime_providers",
    "reset_stage4_lite_runtime_context_factory",
    "reset_stage4_lite_host_config_adapter",
    "reset_stage4_lite_host_adapters",
    "reset_stage4_lite_runtime_providers",
    "refresh_runtime_registry_for_import_gate",
    "refresh_skill_runtime_catalog",
    "resolve_skill_runtime_config_from_env",
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
