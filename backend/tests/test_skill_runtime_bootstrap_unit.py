from fastapi import FastAPI
import pytest

from types import SimpleNamespace

from app.services.skills.bootstrap import (
    EnvHostConfigAdapter,
    RuntimeBootstrapSpec,
    SkillRuntimeRouteMountOptions,
    SkillRuntimeConfig,
    SkillRuntimeRouteStrategy,
    bootstrap_skill_runtime_lifespan,
    bootstrap_skill_runtime_app,
    build_skill_runtime_bootstrap_spec_from_env,
    build_skill_runtime,
    build_stage4_lite_runtime_singletons,
    mount_skill_runtime_routes,
    resolve_runtime_skill_directories,
    resolve_skill_runtime_config_from_env,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.runtime_catalog import RUNTIME_MODE_IMPORT_GATE, RUNTIME_MODE_LEGACY


def test_resolve_skill_runtime_config_from_env_uses_explicit_overrides(monkeypatch, tmp_path):
    builtin_dir = tmp_path / "builtin"
    workspace_dir = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    data_dir = tmp_path / "data"
    monkeypatch.setenv("YUE_BUILTIN_SKILLS_DIR", str(builtin_dir))
    monkeypatch.setenv("YUE_WORKSPACE_SKILLS_DIR", str(workspace_dir))
    monkeypatch.setenv("YUE_USER_SKILLS_DIR", str(user_dir))
    monkeypatch.setenv("YUE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "legacy")
    monkeypatch.setenv("YUE_SKILLS_WATCH_ENABLED", "false")
    monkeypatch.setenv("YUE_SKILLS_RELOAD_DEBOUNCE_MS", "3456")

    config = resolve_skill_runtime_config_from_env()

    assert config.builtin_skills_dir == str(builtin_dir.resolve())
    assert config.workspace_skills_dir == str(workspace_dir.resolve())
    assert config.user_skills_dir == str(user_dir.resolve())
    assert config.data_dir == str(data_dir.resolve())
    assert config.runtime_mode == RUNTIME_MODE_LEGACY
    assert config.watch_enabled is False
    assert config.reload_debounce_ms == 3456


def test_resolve_skill_runtime_config_from_env_prefers_neutral_runtime_keys(monkeypatch, tmp_path):
    neutral_builtin = tmp_path / "neutral-builtin"
    yue_builtin = tmp_path / "yue-builtin"
    monkeypatch.setenv("SKILL_RUNTIME_BUILTIN_SKILLS_DIR", str(neutral_builtin))
    monkeypatch.setenv("YUE_BUILTIN_SKILLS_DIR", str(yue_builtin))
    monkeypatch.setenv("SKILL_RUNTIME_MODE", "legacy")
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "import_gate")

    config = resolve_skill_runtime_config_from_env()

    assert config.builtin_skills_dir == str(neutral_builtin.resolve())
    assert config.runtime_mode == RUNTIME_MODE_LEGACY


def test_resolve_skill_runtime_config_from_env_supports_custom_host_key_aliases(tmp_path):
    runtime_builtin = tmp_path / "runtime-builtin"
    host_adapter = EnvHostConfigAdapter(
        env={"HOST_SKILL_BUILTIN_DIR": str(runtime_builtin)},
        key_aliases={"SKILL_RUNTIME_BUILTIN_SKILLS_DIR": ("HOST_SKILL_BUILTIN_DIR",)},
    )

    config = resolve_skill_runtime_config_from_env(host_config_adapter=host_adapter)

    assert config.builtin_skills_dir == str(runtime_builtin.resolve())


def test_build_skill_runtime_bootstrap_spec_from_env_reads_route_options():
    host_adapter = EnvHostConfigAdapter(
        env={
            "SKILL_RUNTIME_API_PREFIX": "/runtime-api",
            "SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS": "false",
            "SKILL_RUNTIME_INCLUDE_SKILL_GROUPS": "true",
        }
    )

    spec = build_skill_runtime_bootstrap_spec_from_env(host_config_adapter=host_adapter)

    assert spec.config is not None
    assert spec.route_options is not None
    assert spec.route_options.api_prefix == "/runtime-api"
    assert spec.route_options.include_skill_imports is False
    assert spec.route_options.include_skill_groups is True


def test_build_skill_runtime_bootstrap_spec_static_readonly_forces_readonly_routes():
    host_adapter = EnvHostConfigAdapter(
        env={
            "SKILL_RUNTIME_STATIC_READONLY": "true",
            "SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS": "true",
            "SKILL_RUNTIME_INCLUDE_SKILL_GROUPS": "true",
        }
    )

    spec = build_skill_runtime_bootstrap_spec_from_env(host_config_adapter=host_adapter)

    assert spec.route_options is not None
    assert spec.route_options.include_skill_imports is False
    assert spec.route_options.include_skill_groups is False


def test_build_stage4_lite_runtime_singletons_uses_configured_data_dir(tmp_path):
    data_dir = tmp_path / "runtime-data"
    config = SkillRuntimeConfig(
        builtin_skills_dir=str(tmp_path / "builtin"),
        workspace_skills_dir=str(tmp_path / "workspace"),
        user_skills_dir=str(tmp_path / "user"),
        data_dir=str(data_dir),
        runtime_mode=RUNTIME_MODE_IMPORT_GATE,
        watch_enabled=False,
        reload_debounce_ms=2000,
    )
    fake_router = object()

    singletons = build_stage4_lite_runtime_singletons(
        config=config,
        router_factory=lambda _registry: fake_router,
    )

    assert singletons.skill_router is fake_router
    assert singletons.skill_import_store.data_dir == str(data_dir)
    assert singletons.skill_import_service.import_store is singletons.skill_import_store


def test_build_skill_runtime_delegates_to_runtime_singletons_builder(tmp_path):
    config = SkillRuntimeConfig(
        builtin_skills_dir=str(tmp_path / "builtin"),
        workspace_skills_dir=str(tmp_path / "workspace"),
        user_skills_dir=str(tmp_path / "user"),
        data_dir=str(tmp_path / "data"),
        runtime_mode=RUNTIME_MODE_IMPORT_GATE,
        watch_enabled=False,
        reload_debounce_ms=2000,
    )

    built = build_skill_runtime(config=config)

    assert built.skill_registry is not None
    assert built.skill_router is not None
    assert built.skill_import_store.data_dir == str((tmp_path / "data").resolve())


def test_resolve_runtime_skill_directories_uses_projected_import_dirs_in_import_gate(tmp_path):
    projected = [
        SimpleNamespace(layer="import", path=str((tmp_path / "import-skill").resolve())),
    ]
    config = SkillRuntimeConfig(
        builtin_skills_dir=str(tmp_path / "builtin"),
        workspace_skills_dir=str(tmp_path / "workspace"),
        user_skills_dir=str(tmp_path / "user"),
        data_dir=str(tmp_path / "data"),
        runtime_mode=RUNTIME_MODE_IMPORT_GATE,
        watch_enabled=False,
        reload_debounce_ms=2000,
    )

    resolved = resolve_runtime_skill_directories(
        config=config,
        import_store=object(),
        projector_factory=lambda _store: SimpleNamespace(project_active_import_dirs=lambda: projected),
    )

    assert resolved == projected


def test_resolve_runtime_skill_directories_uses_configured_layers_in_legacy_mode(tmp_path):
    config = SkillRuntimeConfig(
        builtin_skills_dir=str(tmp_path / "builtin"),
        workspace_skills_dir=str(tmp_path / "workspace"),
        user_skills_dir=str(tmp_path / "user"),
        data_dir=str(tmp_path / "data"),
        runtime_mode=RUNTIME_MODE_LEGACY,
        watch_enabled=True,
        reload_debounce_ms=2000,
    )

    resolved = resolve_runtime_skill_directories(config=config, import_store=object())

    assert [item.layer for item in resolved] == ["builtin", "workspace", "user"]
    assert [item.path for item in resolved] == [
        str((tmp_path / "builtin").resolve()),
        str((tmp_path / "workspace").resolve()),
        str((tmp_path / "user").resolve()),
    ]


def test_mount_skill_runtime_routes_mounts_expected_endpoints():
    app = FastAPI()

    mount_skill_runtime_routes(app)

    route_paths = {route.path for route in app.routes}
    assert "/api/skills/" in route_paths
    assert "/api/skill-imports/" in route_paths
    assert "/api/skill-preflight/" in route_paths
    assert "/api/skill-groups/" in route_paths


def test_mount_skill_runtime_routes_can_disable_optional_routes():
    app = FastAPI()

    mount_skill_runtime_routes(
        app,
        include_skill_imports=False,
        include_skill_groups=False,
    )

    route_paths = {route.path for route in app.routes}
    assert "/api/skills/" in route_paths
    assert "/api/skill-imports/" not in route_paths
    assert "/api/skill-preflight/" not in route_paths
    assert "/api/skill-groups/" not in route_paths


def test_mount_skill_runtime_routes_uses_route_strategy_when_provided():
    class FakeRouteStrategy(SkillRuntimeRouteStrategy):
        def __init__(self):
            self.calls = []

        def mount(self, app, options: SkillRuntimeRouteMountOptions) -> None:
            self.calls.append((app, options))

    app = FastAPI()
    strategy = FakeRouteStrategy()

    mount_skill_runtime_routes(
        app,
        route_strategy=strategy,
        route_options=SkillRuntimeRouteMountOptions(api_prefix="/v2"),
    )

    assert len(strategy.calls) == 1
    _called_app, options = strategy.calls[0]
    assert options.api_prefix == "/v2"


def test_bootstrap_skill_runtime_app_mounts_with_spec_options():
    app = FastAPI()
    spec = RuntimeBootstrapSpec(
        route_options=SkillRuntimeRouteMountOptions(
            api_prefix="/host-api",
            include_skill_imports=False,
            include_skill_groups=False,
        )
    )

    returned_spec = bootstrap_skill_runtime_app(app, bootstrap_spec=spec)

    assert returned_spec is spec
    route_paths = {route.path for route in app.routes}
    assert "/host-api/skills/" in route_paths
    assert "/host-api/skill-imports/" not in route_paths
    assert "/host-api/skill-groups/" not in route_paths


@pytest.mark.asyncio
async def test_bootstrap_skill_runtime_lifespan_runs_registry_and_hooks(tmp_path):
    events = []
    workspace_dir = tmp_path / "workspace"
    skill_dir = workspace_dir / "lifespan-preflight-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: lifespan-preflight-skill
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
---
## System Prompt
You are a test skill.
""",
        encoding="utf-8",
    )

    class FakeRegistry:
        def __init__(self):
            self.layered_skill_dirs = []
            self.skill_dirs = []
            self.watch_started = False
            self.watch_stopped = False

        def set_layered_skill_dirs(self, layered_skill_dirs):
            self.layered_skill_dirs = list(layered_skill_dirs)

        def load_all(self):
            events.append("load_all")

        def start_runtime_watch(self, layer: str, debounce_ms: int):
            self.watch_started = True
            events.append(f"watch:{layer}:{debounce_ms}")

        def stop_runtime_watch(self):
            self.watch_stopped = True
            events.append("stop_watch")

    registry = FakeRegistry()
    import_store = SkillImportStore(data_dir=str(tmp_path / "data"))
    runtime_context = SimpleNamespace(skill_registry=registry, skill_import_store=import_store)
    spec = RuntimeBootstrapSpec(
        config=SkillRuntimeConfig(
            builtin_skills_dir=str(tmp_path / "builtin"),
            workspace_skills_dir=str(tmp_path / "workspace"),
            user_skills_dir=str(tmp_path / "user"),
            data_dir=str(tmp_path / "data"),
            runtime_mode=RUNTIME_MODE_LEGACY,
            watch_enabled=True,
            reload_debounce_ms=2500,
        )
    )

    async def on_startup():
        events.append("startup")

    async def on_shutdown():
        events.append("shutdown")

    lifespan = bootstrap_skill_runtime_lifespan(
        runtime_context_provider=lambda: runtime_context,
        bootstrap_spec=spec,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )

    async with lifespan(FastAPI()):
        assert registry.watch_started is True
        assert workspace_dir.exists()
        assert (tmp_path / "user").exists()

    assert registry.watch_stopped is True
    assert events == ["load_all", "watch:user:2500", "startup", "shutdown", "stop_watch"]
    records = import_store.list_preflight_records()
    by_ref = {item.skill_ref: item for item in records}
    assert "lifespan-preflight-skill:1.0.0" in by_ref
    assert by_ref["lifespan-preflight-skill:1.0.0"].status == "available"


@pytest.mark.asyncio
async def test_bootstrap_skill_runtime_lifespan_skips_watch_in_import_gate(tmp_path):
    class FakeRegistry:
        def __init__(self):
            self.watch_started = False

        def set_layered_skill_dirs(self, layered_skill_dirs):
            self.layered_skill_dirs = list(layered_skill_dirs)

        def load_all(self):
            pass

        def start_runtime_watch(self, layer: str, debounce_ms: int):
            self.watch_started = True

        def stop_runtime_watch(self):
            pass

    registry = FakeRegistry()
    runtime_context = SimpleNamespace(
        skill_registry=registry,
        skill_import_store=SimpleNamespace(
            list_entries=lambda: [],
            replace_preflight_records=lambda _records: None,
        ),
    )
    spec = RuntimeBootstrapSpec(
        config=SkillRuntimeConfig(
            builtin_skills_dir=str(tmp_path / "builtin"),
            workspace_skills_dir=str(tmp_path / "workspace"),
            user_skills_dir=str(tmp_path / "user"),
            data_dir=str(tmp_path / "data"),
            runtime_mode=RUNTIME_MODE_IMPORT_GATE,
            watch_enabled=True,
            reload_debounce_ms=2000,
        )
    )
    lifespan = bootstrap_skill_runtime_lifespan(
        runtime_context_provider=lambda: runtime_context,
        bootstrap_spec=spec,
    )

    async with lifespan(FastAPI()):
        pass

    assert registry.watch_started is False
