from __future__ import annotations

import inspect
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Protocol, Sequence

from app.services.skills.compatibility import SkillCompatibilityEvaluator
from app.services.skills.directories import SkillDirectoryResolver
from app.services.skills.import_service import SkillImportService
from app.services.skills.import_store import SkillImportStore
from app.services.skills.preflight_service import SkillPreflightService
from app.services.skills.registry import SkillRegistry
from app.services.skills.runtime_catalog import (
    RUNTIME_MODE_IMPORT_GATE,
    RUNTIME_MODE_LEGACY,
    is_skill_runtime_static_readonly_enabled,
    resolve_skill_runtime_mode,
)
from app.services.skills.runtime_catalog import RuntimeSkillCatalogProjector

# Transitional bootstrap surface: this is the current primary runtime-construction
# entry for Yue and copy-first hosts, but its default route strategy still carries
# Yue-flavored API assumptions.

DEFAULT_HOST_CONFIG_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "SKILL_RUNTIME_BUILTIN_SKILLS_DIR": (
        "SKILL_RUNTIME_BUILTIN_SKILLS_DIR",
        "YUE_BUILTIN_SKILLS_DIR",
    ),
    "SKILL_RUNTIME_WORKSPACE_SKILLS_DIR": (
        "SKILL_RUNTIME_WORKSPACE_SKILLS_DIR",
        "YUE_WORKSPACE_SKILLS_DIR",
    ),
    "SKILL_RUNTIME_USER_SKILLS_DIR": (
        "SKILL_RUNTIME_USER_SKILLS_DIR",
        "YUE_USER_SKILLS_DIR",
    ),
    "SKILL_RUNTIME_DATA_DIR": (
        "SKILL_RUNTIME_DATA_DIR",
        "YUE_DATA_DIR",
    ),
    "SKILL_RUNTIME_MODE": (
        "SKILL_RUNTIME_MODE",
        "YUE_SKILL_RUNTIME_MODE",
    ),
    "SKILL_RUNTIME_STATIC_READONLY": (
        "SKILL_RUNTIME_STATIC_READONLY",
        "YUE_SKILL_RUNTIME_STATIC_READONLY",
    ),
    "SKILL_RUNTIME_WATCH_ENABLED": (
        "SKILL_RUNTIME_WATCH_ENABLED",
        "YUE_SKILLS_WATCH_ENABLED",
    ),
    "SKILL_RUNTIME_RELOAD_DEBOUNCE_MS": (
        "SKILL_RUNTIME_RELOAD_DEBOUNCE_MS",
        "YUE_SKILLS_RELOAD_DEBOUNCE_MS",
    ),
    "SKILL_RUNTIME_API_PREFIX": (
        "SKILL_RUNTIME_API_PREFIX",
        "YUE_SKILL_RUNTIME_API_PREFIX",
    ),
    "SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS": (
        "SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS",
        "YUE_SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS",
    ),
    "SKILL_RUNTIME_INCLUDE_SKILL_GROUPS": (
        "SKILL_RUNTIME_INCLUDE_SKILL_GROUPS",
        "YUE_SKILL_RUNTIME_INCLUDE_SKILL_GROUPS",
    ),
}


class HostConfigAdapter(Protocol):
    def get(self, key: str) -> str | None:
        ...


class SkillRuntimeRouteStrategy(Protocol):
    def mount(self, app: Any, options: "SkillRuntimeRouteMountOptions") -> None:
        ...


@dataclass(frozen=True)
class SkillRuntimeRouteMountOptions:
    api_prefix: str = "/api"
    include_skill_imports: bool = True
    include_skill_groups: bool = True


@dataclass(frozen=True)
class RuntimeBootstrapSpec:
    config: SkillRuntimeConfig | None = None
    host_config_adapter: HostConfigAdapter | None = None
    route_strategy: SkillRuntimeRouteStrategy | None = None
    route_options: SkillRuntimeRouteMountOptions | None = None
    api_prefix: str = "/api"
    include_skill_imports: bool = True
    include_skill_groups: bool = True


class EnvHostConfigAdapter:
    def __init__(
        self,
        *,
        env: Mapping[str, str] | None = None,
        key_aliases: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._env = env or os.environ
        merged_aliases = dict(DEFAULT_HOST_CONFIG_KEY_ALIASES)
        if key_aliases:
            for key, aliases in key_aliases.items():
                merged_aliases[key] = tuple(aliases)
        self._key_aliases = merged_aliases

    def get(self, key: str) -> str | None:
        aliases = self._key_aliases.get(key, (key,))
        for alias in aliases:
            value = self._env.get(alias)
            if value is not None:
                return value
        return None


class DefaultSkillRuntimeRouteStrategy:
    # Transitional default for copy-first adoption. Package-first hosts should
    # inject a host-local route strategy instead of relying on Yue route modules.
    def mount(self, app: Any, options: SkillRuntimeRouteMountOptions) -> None:
        from app.api import skills as skills_api

        app.include_router(
            skills_api.router,
            prefix=f"{options.api_prefix}/skills",
            tags=["skills"],
        )
        if options.include_skill_imports:
            from app.api import skill_imports as skill_imports_api
            from app.api import skill_preflight as skill_preflight_api

            app.include_router(
                skill_imports_api.router,
                prefix=f"{options.api_prefix}/skill-imports",
                tags=["skill-imports"],
            )
            app.include_router(
                skill_preflight_api.router,
                prefix=f"{options.api_prefix}/skill-preflight",
                tags=["skill-preflight"],
            )
        if options.include_skill_groups:
            from app.api import skill_groups as skill_groups_api

            app.include_router(
                skill_groups_api.router,
                prefix=f"{options.api_prefix}/skill-groups",
                tags=["skill-groups"],
            )


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _flag_from_host_config(adapter: HostConfigAdapter, key: str, default: bool) -> bool:
    raw = adapter.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_host_config(adapter: HostConfigAdapter, key: str, default: int) -> int:
    raw = adapter.get(key)
    if raw is None:
        return default
    try:
        parsed = int(raw)
    except Exception:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class SkillRuntimeConfig:
    builtin_skills_dir: str
    workspace_skills_dir: str
    user_skills_dir: str
    data_dir: str
    runtime_mode: str
    watch_enabled: bool
    reload_debounce_ms: int


@dataclass(frozen=True)
class BuiltSkillRuntime:
    skill_registry: SkillRegistry
    skill_router: Any
    skill_action_execution_service: Any
    skill_import_store: SkillImportStore
    skill_compatibility_evaluator: SkillCompatibilityEvaluator
    skill_import_service: SkillImportService


LifespanHook = Callable[[], Awaitable[None] | None]


def build_skill_runtime(
    *,
    config: SkillRuntimeConfig | None = None,
    router_factory: Callable[[SkillRegistry], Any] | None = None,
    action_service_factory: Callable[[SkillRegistry], Any] | None = None,
) -> BuiltSkillRuntime:
    # Public runtime builder. New runtime construction should point here rather
    # than directly instantiating Stage4 compatibility singletons.
    return build_stage4_lite_runtime_singletons(
        config=config,
        router_factory=router_factory,
        action_service_factory=action_service_factory,
    )


def build_skill_runtime_bootstrap_spec_from_env(
    *,
    host_config_adapter: HostConfigAdapter | None = None,
    key_aliases: Mapping[str, Sequence[str]] | None = None,
    env: Mapping[str, str] | None = None,
    route_strategy: SkillRuntimeRouteStrategy | None = None,
) -> RuntimeBootstrapSpec:
    host_config = host_config_adapter or EnvHostConfigAdapter(env=env, key_aliases=key_aliases)
    route_options = _resolve_route_mount_options(host_config, "/api", True, True)
    return RuntimeBootstrapSpec(
        config=resolve_skill_runtime_config_from_env(host_config_adapter=host_config),
        host_config_adapter=host_config,
        route_strategy=route_strategy,
        route_options=route_options,
        api_prefix=route_options.api_prefix,
        include_skill_imports=route_options.include_skill_imports,
        include_skill_groups=route_options.include_skill_groups,
    )


def resolve_skill_runtime_config_from_env(
    *,
    host_config_adapter: HostConfigAdapter | None = None,
    key_aliases: Mapping[str, Sequence[str]] | None = None,
    env: Mapping[str, str] | None = None,
) -> SkillRuntimeConfig:
    backend_root = Path(__file__).resolve().parents[3]
    workspace_root = Path(__file__).resolve().parents[4]
    host_config = host_config_adapter or EnvHostConfigAdapter(env=env, key_aliases=key_aliases)
    builtin_skills_dir = Path(
        host_config.get("SKILL_RUNTIME_BUILTIN_SKILLS_DIR") or str(backend_root / "data" / "skills")
    ).expanduser().resolve()
    workspace_skills_dir = Path(
        host_config.get("SKILL_RUNTIME_WORKSPACE_SKILLS_DIR") or str(workspace_root / "data" / "skills")
    ).expanduser().resolve()
    user_skills_dir = Path(
        host_config.get("SKILL_RUNTIME_USER_SKILLS_DIR") or str(Path.home() / ".yue" / "skills")
    ).expanduser().resolve()
    data_dir = Path(
        host_config.get("SKILL_RUNTIME_DATA_DIR") or str(Path.home() / ".yue" / "data")
    ).expanduser().resolve()
    return SkillRuntimeConfig(
        builtin_skills_dir=str(builtin_skills_dir),
        workspace_skills_dir=str(workspace_skills_dir),
        user_skills_dir=str(user_skills_dir),
        data_dir=str(data_dir),
        runtime_mode=resolve_skill_runtime_mode(host_config.get("SKILL_RUNTIME_MODE")),
        watch_enabled=_flag_from_host_config(host_config, "SKILL_RUNTIME_WATCH_ENABLED", True),
        reload_debounce_ms=_int_from_host_config(host_config, "SKILL_RUNTIME_RELOAD_DEBOUNCE_MS", 2000),
    )


def build_stage4_lite_runtime_singletons(
    *,
    config: SkillRuntimeConfig | None = None,
    router_factory: Callable[[SkillRegistry], Any] | None = None,
    action_service_factory: Callable[[SkillRegistry], Any] | None = None,
) -> BuiltSkillRuntime:
    # Lower-level constructor kept for compatibility. Prefer build_skill_runtime()
    # when choosing the primary runtime-construction entry.
    from app.services.skills.actions import SkillActionExecutionService
    from app.services.skills.routing import SkillRouter
    from app.services.agent_store import agent_store

    effective_config = config or resolve_skill_runtime_config_from_env()
    registry = SkillRegistry()
    router_builder = router_factory or (lambda resolved_registry: SkillRouter(resolved_registry))
    action_builder = action_service_factory or (lambda resolved_registry: SkillActionExecutionService(resolved_registry))
    router = router_builder(registry)
    action_execution_service = action_builder(registry)
    import_store = SkillImportStore(data_dir=effective_config.data_dir)
    compatibility_evaluator = SkillCompatibilityEvaluator()
    import_service = SkillImportService(
        import_store=import_store,
        compatibility_evaluator=compatibility_evaluator,
        agent_store=agent_store,
    )
    return BuiltSkillRuntime(
        skill_registry=registry,
        skill_router=router,
        skill_action_execution_service=action_execution_service,
        skill_import_store=import_store,
        skill_compatibility_evaluator=compatibility_evaluator,
        skill_import_service=import_service,
    )


def resolve_runtime_skill_directories(
    *,
    config: SkillRuntimeConfig,
    import_store: SkillImportStore | Any,
    projector_factory: Callable[[Any], Any] | None = None,
):
    if config.runtime_mode == RUNTIME_MODE_IMPORT_GATE:
        projector_builder = projector_factory or (lambda store: RuntimeSkillCatalogProjector(import_store=store))
        projector = projector_builder(import_store)
        return projector.project_active_import_dirs()
    resolver = SkillDirectoryResolver(
        builtin_dir=config.builtin_skills_dir,
        workspace_dir=config.workspace_skills_dir,
        user_dir=config.user_skills_dir,
    )
    return resolver.resolve()


def mount_skill_runtime_routes(
    app: Any,
    *,
    api_prefix: str = "/api",
    include_skill_imports: bool = True,
    include_skill_groups: bool = True,
    route_options: SkillRuntimeRouteMountOptions | None = None,
    route_strategy: SkillRuntimeRouteStrategy | None = None,
    host_config_adapter: HostConfigAdapter | None = None,
    bootstrap_spec: RuntimeBootstrapSpec | None = None,
) -> None:
    # Transitional bootstrap entry: explicit and reusable, but the default
    # strategy still mounts Yue route modules unless the host overrides it.
    if bootstrap_spec is None:
        host_config = host_config_adapter or EnvHostConfigAdapter()
        options = route_options or _resolve_route_mount_options(
            host_config,
            api_prefix,
            include_skill_imports,
            include_skill_groups,
        )
        strategy = route_strategy or DefaultSkillRuntimeRouteStrategy()
    else:
        host_config = bootstrap_spec.host_config_adapter or host_config_adapter or EnvHostConfigAdapter()
        options = route_options or bootstrap_spec.route_options or _resolve_route_mount_options(
            host_config,
            bootstrap_spec.api_prefix,
            bootstrap_spec.include_skill_imports,
            bootstrap_spec.include_skill_groups,
        )
        strategy = route_strategy or bootstrap_spec.route_strategy or DefaultSkillRuntimeRouteStrategy()
    strategy.mount(app, options)


def bootstrap_skill_runtime_app(
    app: Any,
    *,
    bootstrap_spec: RuntimeBootstrapSpec | None = None,
) -> RuntimeBootstrapSpec:
    spec = bootstrap_spec or build_skill_runtime_bootstrap_spec_from_env()
    mount_skill_runtime_routes(app, bootstrap_spec=spec)
    return spec


def bootstrap_skill_runtime_lifespan(
    *,
    runtime_context_provider: Callable[[], Any],
    bootstrap_spec: RuntimeBootstrapSpec | None = None,
    runtime_config: SkillRuntimeConfig | None = None,
    on_startup: LifespanHook | None = None,
    on_shutdown: LifespanHook | None = None,
    logger: Any | None = None,
):
    @asynccontextmanager
    async def _lifespan(_app: Any):
        context = runtime_context_provider()
        runtime_registry = context.skill_registry
        spec = bootstrap_spec or build_skill_runtime_bootstrap_spec_from_env()
        config = runtime_config or spec.config or resolve_skill_runtime_config_from_env(
            host_config_adapter=spec.host_config_adapter
        )
        layered_dirs = resolve_runtime_skill_directories(
            config=config,
            import_store=context.skill_import_store,
        )
        preflight_dirs = SkillDirectoryResolver(
            builtin_dir=config.builtin_skills_dir,
            workspace_dir=config.workspace_skills_dir,
            user_dir=config.user_skills_dir,
        ).resolve()
        if config.runtime_mode != RUNTIME_MODE_LEGACY and logger is not None:
            logger.info("Skill runtime mode %s enabled; projected active imports=%s", config.runtime_mode, len(layered_dirs))
        for item in preflight_dirs:
            if item.layer in {"workspace", "user"}:
                Path(item.path).mkdir(parents=True, exist_ok=True)
        compatibility_evaluator = getattr(
            getattr(context, "skill_import_service", None),
            "compatibility_evaluator",
            None,
        )
        preflight_service = SkillPreflightService(
            import_store=context.skill_import_store,
            compatibility_evaluator=compatibility_evaluator,
        )
        preflight_records = preflight_service.refresh(preflight_dirs)
        if logger is not None:
            logger.info("Skill preflight refreshed with %s records", len(preflight_records))
        runtime_registry.set_layered_skill_dirs(layered_dirs)
        runtime_registry.skill_dirs = [item.path for item in layered_dirs]
        runtime_registry.load_all()
        if config.watch_enabled and config.runtime_mode == RUNTIME_MODE_LEGACY:
            runtime_registry.start_runtime_watch(layer="user", debounce_ms=config.reload_debounce_ms)
        elif config.watch_enabled and logger is not None:
            logger.info("Skill directory watch skipped in import-gate runtime mode")

        await _run_lifespan_hook(on_startup)
        try:
            yield
        finally:
            await _run_lifespan_hook(on_shutdown)
            runtime_registry.stop_runtime_watch()

    return _lifespan


async def _run_lifespan_hook(hook: LifespanHook | None) -> None:
    if hook is None:
        return
    maybe_awaitable = hook()
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


def _resolve_route_mount_options(
    host_config: HostConfigAdapter,
    api_prefix: str,
    include_skill_imports: bool,
    include_skill_groups: bool,
) -> SkillRuntimeRouteMountOptions:
    static_readonly_enabled = _flag_from_host_config(
        host_config,
        "SKILL_RUNTIME_STATIC_READONLY",
        is_skill_runtime_static_readonly_enabled(),
    )
    include_imports = _flag_from_host_config(
        host_config,
        "SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS",
        include_skill_imports,
    )
    include_groups = _flag_from_host_config(
        host_config,
        "SKILL_RUNTIME_INCLUDE_SKILL_GROUPS",
        include_skill_groups,
    )
    if static_readonly_enabled:
        include_imports = False
        include_groups = False
    return SkillRuntimeRouteMountOptions(
        api_prefix=host_config.get("SKILL_RUNTIME_API_PREFIX") or api_prefix,
        include_skill_imports=include_imports,
        include_skill_groups=include_groups,
    )
