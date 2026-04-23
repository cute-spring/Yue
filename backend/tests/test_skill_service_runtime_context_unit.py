from app.services import skill_service as skill_service_module


def test_stage4_runtime_context_factory_can_be_overridden_and_reset():
    baseline = skill_service_module.get_stage4_lite_runtime_context()

    class FakeContext:
        def __init__(self):
            self.skill_registry = "registry"
            self.skill_router = "router"
            self.skill_action_execution_service = "action_service"
            self.skill_import_store = "import_store"

    fake_context = FakeContext()

    try:
        skill_service_module.set_stage4_lite_runtime_context_factory(lambda: fake_context)
        resolved = skill_service_module.get_stage4_lite_runtime_context()
        assert resolved is fake_context
    finally:
        skill_service_module.reset_stage4_lite_runtime_context_factory()

    restored = skill_service_module.get_stage4_lite_runtime_context()
    assert type(restored) is type(baseline)
    assert restored.skill_registry is skill_service_module.skill_registry


def test_stage4_runtime_providers_can_be_overridden_and_reset():
    baseline = skill_service_module.get_stage4_lite_runtime_context()
    fake_registry = object()
    fake_router = object()
    fake_action_service = object()
    fake_import_store = object()

    providers = skill_service_module.Stage4LiteRuntimeProviders(
        registry=lambda: fake_registry,
        router=lambda: fake_router,
        action_execution_service=lambda: fake_action_service,
        import_store=lambda: fake_import_store,
        import_service=lambda: object(),
    )

    try:
        skill_service_module.set_stage4_lite_runtime_providers(providers)
        resolved = skill_service_module.get_stage4_lite_runtime_context()
        assert resolved.skill_registry is fake_registry
        assert resolved.skill_router is fake_router
        assert resolved.skill_action_execution_service is fake_action_service
        assert resolved.skill_import_store is fake_import_store
    finally:
        skill_service_module.reset_stage4_lite_runtime_providers()

    restored = skill_service_module.get_stage4_lite_runtime_context()
    assert type(restored) is type(baseline)
    assert restored.skill_registry is skill_service_module.skill_registry
    assert restored.skill_router is skill_service_module.skill_router
    assert restored.skill_action_execution_service is skill_service_module.skill_action_execution_service
    assert restored.skill_import_store is skill_service_module.skill_import_store


def test_build_stage4_lite_runtime_seams_defaults_to_runtime_context_providers():
    class FakeStore:
        def __init__(self):
            self.list_entries_calls = 0

        def list_entries(self):
            self.list_entries_calls += 1
            return []

    class FakeRouter:
        def __init__(self):
            self.resolve_calls = 0

        def resolve_visible_skill_refs(self, _agent):
            self.resolve_calls += 1
            return ["planner:1.0.0"]

    fake_store = FakeStore()
    fake_router = FakeRouter()
    providers = skill_service_module.Stage4LiteRuntimeProviders(
        registry=lambda: object(),
        router=lambda: fake_router,
        action_execution_service=lambda: object(),
        import_store=lambda: fake_store,
        import_service=lambda: object(),
    )
    agent = type("Agent", (), {})()

    try:
        skill_service_module.set_stage4_lite_runtime_providers(providers)
        seams = skill_service_module.build_stage4_lite_runtime_seams()
        refs = seams.activation_state_store.list_active_source_refs()
        visible = seams.visibility_resolver.resolve_visible_skill_refs(agent)
    finally:
        skill_service_module.reset_stage4_lite_runtime_providers()

    assert refs == []
    assert visible == ["planner:1.0.0"]
    assert fake_store.list_entries_calls == 1
    assert fake_router.resolve_calls == 1


def test_refresh_skill_runtime_catalog_uses_runtime_context_providers():
    class FakeRegistry:
        def __init__(self):
            self.layered_skill_dirs = []
            self.skill_dirs = []

        def set_layered_skill_dirs(self, layered_skill_dirs):
            self.layered_skill_dirs = list(layered_skill_dirs)

        def load_all(self):
            self.skill_dirs = [item.path for item in self.layered_skill_dirs]

    class FakeStore:
        def list_entries(self):
            return []

    fake_registry = FakeRegistry()
    fake_store = FakeStore()
    providers = skill_service_module.Stage4LiteRuntimeProviders(
        registry=lambda: fake_registry,
        router=lambda: object(),
        action_execution_service=lambda: object(),
        import_store=lambda: fake_store,
        import_service=lambda: object(),
    )

    previous_runtime_mode = skill_service_module.resolve_skill_runtime_mode

    try:
        skill_service_module.set_stage4_lite_runtime_providers(providers)
        skill_service_module.resolve_skill_runtime_mode = lambda *_args, **_kwargs: skill_service_module.RUNTIME_MODE_IMPORT_GATE
        refreshed = skill_service_module.refresh_skill_runtime_catalog()
    finally:
        skill_service_module.resolve_skill_runtime_mode = previous_runtime_mode
        skill_service_module.reset_stage4_lite_runtime_providers()

    assert refreshed is True
    assert fake_registry.layered_skill_dirs == []
    assert fake_registry.skill_dirs == []


def test_default_runtime_context_is_not_driven_by_module_singleton_aliases():
    baseline = skill_service_module.get_stage4_lite_runtime_context()
    original_registry = skill_service_module.skill_registry
    original_router = skill_service_module.skill_router
    original_action_service = skill_service_module.skill_action_execution_service
    original_import_store = skill_service_module.skill_import_store
    original_import_service = skill_service_module.skill_import_service

    try:
        skill_service_module.skill_registry = object()
        skill_service_module.skill_router = object()
        skill_service_module.skill_action_execution_service = object()
        skill_service_module.skill_import_store = object()
        skill_service_module.skill_import_service = object()

        resolved = skill_service_module.get_stage4_lite_runtime_context()
    finally:
        skill_service_module.skill_registry = original_registry
        skill_service_module.skill_router = original_router
        skill_service_module.skill_action_execution_service = original_action_service
        skill_service_module.skill_import_store = original_import_store
        skill_service_module.skill_import_service = original_import_service

    assert resolved.skill_registry is baseline.skill_registry
    assert resolved.skill_router is baseline.skill_router
    assert resolved.skill_action_execution_service is baseline.skill_action_execution_service
    assert resolved.skill_import_store is baseline.skill_import_store
    assert resolved.skill_import_service is baseline.skill_import_service
