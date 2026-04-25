from app.services import skill_service as skill_service_module


def test_stage4_singleton_builder_delegates_to_public_runtime_builder(monkeypatch):
    fake_runtime = skill_service_module.BuiltSkillRuntime(
        skill_registry=object(),
        skill_router=object(),
        skill_action_execution_service=object(),
        skill_import_store=object(),
        skill_compatibility_evaluator=object(),
        skill_import_service=object(),
    )
    calls = []

    def fake_build_skill_runtime(**kwargs):
        calls.append(kwargs)
        return fake_runtime

    monkeypatch.setattr(skill_service_module, "build_skill_runtime", fake_build_skill_runtime)

    built = skill_service_module._build_stage4_lite_runtime_singletons()

    assert len(calls) == 1
    assert built.skill_registry is fake_runtime.skill_registry
    assert built.skill_router is fake_runtime.skill_router
    assert built.skill_action_execution_service is fake_runtime.skill_action_execution_service
    assert built.skill_import_store is fake_runtime.skill_import_store
    assert built.skill_import_service is fake_runtime.skill_import_service


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


def test_stage4_host_adapters_can_be_overridden_and_reset():
    baseline = skill_service_module.get_stage4_lite_host_adapters()
    fake_agent_provider = object()
    fake_feature_flag_provider = object()
    fake_skill_group_resolver = object()

    adapters = skill_service_module.Stage4LiteHostAdapters(
        agent_provider=fake_agent_provider,
        feature_flag_provider=fake_feature_flag_provider,
        skill_group_resolver=fake_skill_group_resolver,
    )

    try:
        skill_service_module.set_stage4_lite_host_adapters(adapters)
        resolved = skill_service_module.get_stage4_lite_host_adapters()
        assert resolved.agent_provider is fake_agent_provider
        assert resolved.feature_flag_provider is fake_feature_flag_provider
        assert resolved.skill_group_resolver is fake_skill_group_resolver
    finally:
        skill_service_module.reset_stage4_lite_host_adapters()

    restored = skill_service_module.get_stage4_lite_host_adapters()
    assert type(restored) is type(baseline)
    assert restored.agent_provider is not fake_agent_provider
    assert restored.feature_flag_provider is not fake_feature_flag_provider
    assert restored.skill_group_resolver is not fake_skill_group_resolver


def test_stage4_host_adapter_override_updates_runtime_router_group_resolver():
    class FakeSkillGroupResolver:
        def get_skill_refs_by_group_ids(self, _group_ids):
            return ["planner:9.9.9"]

    fake_resolver = FakeSkillGroupResolver()
    adapters = skill_service_module.Stage4LiteHostAdapters(
        agent_provider=object(),
        feature_flag_provider=object(),
        skill_group_resolver=fake_resolver,
    )

    original_router_store = skill_service_module.skill_router.skill_group_store
    try:
        skill_service_module.set_stage4_lite_host_adapters(adapters)
        assert skill_service_module.skill_router.skill_group_store is fake_resolver
        assert skill_service_module.skill_router.resolve_visible_skill_refs(
            type("Agent", (), {"skill_groups": ["g1"], "resolved_visible_skills": [], "extra_visible_skills": [], "visible_skills": []})()
        ) == ["planner:9.9.9"]
    finally:
        skill_service_module.reset_stage4_lite_host_adapters()

    restored_store = skill_service_module.skill_router.skill_group_store
    assert restored_store is not fake_resolver
    assert restored_store is not None
    assert hasattr(restored_store, "get_skill_refs_by_group_ids")
    assert type(restored_store) is type(original_router_store)


def test_stage4_host_adapters_can_supply_custom_visibility_resolver():
    class FakeVisibilityResolver:
        def __init__(self):
            self.skill_group_store = None

        def resolve_visible_skill_refs(self, _agent):
            return ["host-resolver:1.0.0"]

    adapters = skill_service_module.Stage4LiteHostAdapters(
        agent_provider=object(),
        feature_flag_provider=object(),
        skill_group_resolver=object(),
        visibility_resolver=FakeVisibilityResolver(),
    )

    try:
        skill_service_module.set_stage4_lite_host_adapters(adapters)
        resolved = skill_service_module.skill_router.resolve_visible_skill_refs(object())
    finally:
        skill_service_module.reset_stage4_lite_host_adapters()

    assert resolved == ["host-resolver:1.0.0"]


def test_refresh_runtime_catalog_defaults_to_runtime_context_path():
    class FakeRegistry:
        def __init__(self):
            self.layered_skill_dirs = None
            self.skill_dirs = None

        def set_layered_skill_dirs(self, layered_skill_dirs):
            self.layered_skill_dirs = list(layered_skill_dirs)

        def load_all(self):
            self.skill_dirs = [item.path for item in (self.layered_skill_dirs or [])]

    class FakeStore:
        def list_entries(self):
            return []

    fake_registry = FakeRegistry()
    fake_store = FakeStore()
    previous_runtime_mode = skill_service_module.resolve_skill_runtime_mode

    try:
        skill_service_module.set_stage4_lite_runtime_context_factory(
            lambda: skill_service_module.Stage4LiteRuntimeContext(
                skill_registry=fake_registry,
                skill_router=object(),
                skill_action_execution_service=object(),
                skill_import_store=fake_store,
                skill_import_service=object(),
            )
        )
        skill_service_module.resolve_skill_runtime_mode = (
            lambda *_args, **_kwargs: skill_service_module.RUNTIME_MODE_IMPORT_GATE
        )
        refreshed = skill_service_module.refresh_skill_runtime_catalog()
    finally:
        skill_service_module.resolve_skill_runtime_mode = previous_runtime_mode
        skill_service_module.reset_stage4_lite_runtime_context_factory()

    assert refreshed is True
    assert fake_registry.layered_skill_dirs == []
    assert fake_registry.skill_dirs == []


def test_stage4_host_config_adapter_can_be_set_and_reset():
    class FakeHostConfigAdapter:
        def get(self, key: str):
            return "value" if key == "SKILL_RUNTIME_MODE" else None

    try:
        skill_service_module.set_stage4_lite_host_config_adapter(FakeHostConfigAdapter())
        adapter = skill_service_module.get_stage4_lite_host_config_adapter()
        assert adapter is not None
        assert adapter.get("SKILL_RUNTIME_MODE") == "value"
    finally:
        skill_service_module.reset_stage4_lite_host_config_adapter()

    assert skill_service_module.get_stage4_lite_host_config_adapter() is None


def test_register_stage4_host_runtime_adapter_bundle_updates_adapters_and_host_config():
    class FakeAgentProvider:
        def get_agent(self, _agent_id: str):
            return None

    class FakeFeatureFlagProvider:
        def get_feature_flags(self):
            return {"skill_runtime_enabled": True}

    class FakeSkillGroupResolver:
        def get_skill_refs_by_group_ids(self, _group_ids):
            return ["planner:1.0.0"]

    class FakeHostConfigAdapter:
        def get(self, key: str):
            if key == "SKILL_RUNTIME_API_PREFIX":
                return "/custom-api"
            return None

    bundle = skill_service_module.HostRuntimeAdapterBundle(
        agent_provider=FakeAgentProvider(),
        feature_flag_provider=FakeFeatureFlagProvider(),
        skill_group_resolver=FakeSkillGroupResolver(),
        host_config_provider=FakeHostConfigAdapter(),
    )
    baseline = skill_service_module.get_stage4_lite_host_adapters()
    baseline_host_config = skill_service_module.get_stage4_lite_host_config_adapter()

    try:
        registered = skill_service_module.register_stage4_lite_host_runtime_adapter_bundle(bundle)
        adapters = skill_service_module.get_stage4_lite_host_adapters()
        host_config = skill_service_module.get_stage4_lite_host_config_adapter()
        assert registered is bundle
        assert adapters.agent_provider is bundle.agent_provider
        assert adapters.feature_flag_provider is bundle.feature_flag_provider
        assert adapters.skill_group_resolver is bundle.skill_group_resolver
        assert host_config is bundle.host_config_provider
    finally:
        skill_service_module.set_stage4_lite_host_adapters(baseline)
        skill_service_module.set_stage4_lite_host_config_adapter(baseline_host_config)
