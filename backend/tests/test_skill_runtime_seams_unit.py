from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from app.services import chat_prompting
from app.services.skill_service import build_stage4_lite_runtime_seams
from app.services.skills.import_models import (
    SkillImportLifecycleState,
    SkillImportPreview,
    SkillImportRecord,
    SkillImportReport,
    SkillImportSourceType,
    SkillImportStoredEntry,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillConstraints, SkillSpec
from app.services.skills.host_adapters import GroupAwareAgentVisibilityResolver
from app.services.skills.runtime_seams import build_skill_runtime_seams
from app.services.skills.routing import SkillRouter
from app.services.skills.registry import SkillRegistry


def _entry(
    *,
    skill_name: str,
    source_ref: str,
    lifecycle_state: SkillImportLifecycleState,
    source_type: SkillImportSourceType = SkillImportSourceType.DIRECTORY,
) -> SkillImportStoredEntry:
    record = SkillImportRecord(
        skill_name=skill_name,
        skill_version="1.0.0",
        display_name=skill_name,
        source_type=source_type,
        source_ref=source_ref,
        package_format="package_directory",
        lifecycle_state=lifecycle_state,
        updated_at=datetime.utcnow(),
    )
    return SkillImportStoredEntry(
        record=record,
        report=SkillImportReport(
            import_id=record.id,
            parse_status="passed",
            standard_validation_status="passed",
            compatibility_status="compatible",
            activation_eligibility="eligible",
        ),
        preview=SkillImportPreview(
            skill_name=skill_name,
            skill_version="1.0.0",
            description="test",
            capabilities=[],
            entrypoint="system_prompt",
        ),
    )


def _write_skill_package(root: Path, name: str) -> Path:
    package_dir = root / name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        f"""---
name: {name}
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
    return package_dir


def test_stage4_lite_runtime_seams_can_be_built_without_app_startup():
    seams = build_stage4_lite_runtime_seams()
    assert seams.tool_capability_provider is not None
    assert seams.activation_state_store is not None
    assert seams.runtime_catalog_projector is not None
    assert seams.prompt_injection_adapter is not None
    assert seams.visibility_resolver is not None


def test_stage4_lite_runtime_seams_accept_explicit_overrides(tmp_path):
    active_dir = _write_skill_package(tmp_path, "override-active-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="override-active-skill",
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
        )
    )
    router = SkillRouter(SkillRegistry())
    seams = build_stage4_lite_runtime_seams(import_store=store, router=router)

    projected = seams.runtime_catalog_projector.project_active_import_dirs()
    refs = seams.activation_state_store.list_active_source_refs()

    assert [item.path for item in projected] == [str(active_dir.resolve())]
    assert refs == [str(active_dir)]


def test_build_skill_runtime_seams_projects_import_dirs_and_activation_refs(tmp_path):
    active_dir = _write_skill_package(tmp_path, "active-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="active-skill",
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
        )
    )
    store.save_entry(
        _entry(
            skill_name="inactive-skill",
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.INACTIVE,
        )
    )
    registry = SkillRegistry()
    router = SkillRouter(registry)

    seams = build_skill_runtime_seams(import_store=store, router=router)
    projected = seams.runtime_catalog_projector.project_active_import_dirs()
    refs = seams.activation_state_store.list_active_source_refs()

    assert [item.path for item in projected] == [str(active_dir.resolve())]
    assert refs == [str(active_dir)]


def test_stage4_lite_tool_capability_provider_and_prompt_injection_adapter():
    seams = build_stage4_lite_runtime_seams()
    skill = SkillSpec(
        name="planner",
        version="1.0.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        constraints=SkillConstraints(allowed_tools=["builtin:docs_read"]),
    )
    effective_tools = seams.tool_capability_provider.resolve_effective_tools(
        agent_tools=["builtin:docs_read", "builtin:exec"],
        skill=skill,
    )
    composed = seams.prompt_injection_adapter.compose_prompt(
        base_prompt="Base prompt.",
        skill_prompt="Skill prompt.",
    )

    assert effective_tools == ["builtin:docs_read"]
    assert composed == "Base prompt.\n\nSkill prompt."


def test_stage4_lite_visibility_resolver_matches_router_refs():
    registry = SkillRegistry()
    router = SkillRouter(registry)
    seams = build_skill_runtime_seams(import_store=SkillImportStore(), router=router)
    agent = type(
        "Agent",
        (),
        {
            "resolved_visible_skills": [],
            "skill_groups": [],
            "extra_visible_skills": [],
            "visible_skills": ["planner:1.0.0", "planner:1.0.0", "coder:2.0.0"],
        },
    )()

    resolved = seams.visibility_resolver.resolve_visible_skill_refs(agent)
    assert resolved == ["planner:1.0.0", "coder:2.0.0"]


def test_skill_router_prefers_injected_visibility_resolver_store():
    class _StoreA:
        def get_skill_refs_by_group_ids(self, group_ids):
            return ["from-resolver:1.0.0"] if group_ids == ["g1"] else []

    class _StoreB:
        def get_skill_refs_by_group_ids(self, group_ids):
            return ["from-router:1.0.0"] if group_ids == ["g1"] else []

    class _InjectedResolver:
        def __init__(self):
            self.skill_group_store = _StoreA()

        def resolve_visible_skill_refs(self, agent):
            return self.skill_group_store.get_skill_refs_by_group_ids(getattr(agent, "skill_groups", []) or [])

    router = SkillRouter(
        SkillRegistry(),
        skill_group_store=_StoreB(),
        visibility_resolver=_InjectedResolver(),
    )
    agent = SimpleNamespace(skill_groups=["g1"])

    resolved = router.resolve_visible_skill_refs(agent)

    assert resolved == ["from-resolver:1.0.0"]


def test_skill_router_keeps_skill_group_store_patch_compatibility():
    class _InitialStore:
        def get_skill_refs_by_group_ids(self, _group_ids):
            return []

    class _PatchedStore:
        def get_skill_refs_by_group_ids(self, group_ids):
            return ["patched:1.0.0"] if group_ids == ["g1"] else []

    router = SkillRouter(
        SkillRegistry(),
        visibility_resolver=GroupAwareAgentVisibilityResolver(skill_group_resolver=_InitialStore()),
    )
    router.skill_group_store = _PatchedStore()
    agent = SimpleNamespace(
        skill_groups=["g1"],
        resolved_visible_skills=[],
        extra_visible_skills=[],
        visible_skills=[],
    )

    resolved = router.resolve_visible_skill_refs(agent)

    assert resolved == ["patched:1.0.0"]


def test_core_skill_router_default_visibility_ignores_group_ids_without_host_resolver():
    router = SkillRouter(SkillRegistry())
    agent = SimpleNamespace(
        skill_groups=["g1"],
        resolved_visible_skills=[],
        extra_visible_skills=[],
        visible_skills=["planner:1.0.0"],
    )

    resolved = router.resolve_visible_skill_refs(agent)

    assert resolved == ["planner:1.0.0"]


def test_resolve_skill_runtime_state_prefers_stage4_visibility_seam():
    fake_chat_service = SimpleNamespace(
        clear_session_skill=lambda _chat_id: None,
        get_session_skill=lambda _chat_id: None,
        set_session_skill=lambda _chat_id, _name, _version: None,
    )
    fake_router = SimpleNamespace(
        resolve_visible_skill_refs=lambda _agent: (_ for _ in ()).throw(AssertionError("router visibility should not be called")),
    )
    runtime_seams = SimpleNamespace(
        visibility_resolver=SimpleNamespace(resolve_visible_skill_refs=lambda _agent: ["planner:1.0.0", "coder:2.0.0"])
    )
    agent = SimpleNamespace(
        skill_mode="off",
        visible_skills=[],
        resolved_visible_skills=[],
    )

    state = chat_prompting.resolve_skill_runtime_state(
        agent_config=agent,
        feature_flags={"skill_runtime_enabled": False},
        chat_id="chat-1",
        request_message="hello",
        requested_skill=None,
        skill_router=fake_router,
        skill_registry=SimpleNamespace(),
        chat_service=fake_chat_service,
        skill_bind_min_score=2,
        skill_switch_delta=2,
        runtime_seams=runtime_seams,
    )

    assert state.selection_reason_code == "skill_mode_off"
    assert state.resolved_skill_count == 2
    assert agent.resolved_visible_skills == ["planner:1.0.0", "coder:2.0.0"]


def test_assemble_runtime_prompt_prefers_stage4_prompt_and_tool_seams():
    selected_skill = SkillSpec(
        name="planner",
        version="1.0.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        constraints=SkillConstraints(allowed_tools=["builtin:docs_read"]),
    )
    fake_descriptor = SimpleNamespace(
        prompt_blocks={
            "system_prompt": "Skill prompt.",
            "instructions": "Follow planner rules.",
        },
        tool_policy={"allowed_tools": ["builtin:docs_read"]},
    )
    fake_markdown_adapter = SimpleNamespace(to_descriptor=lambda _skill: fake_descriptor)
    runtime_seams = SimpleNamespace(
        prompt_injection_adapter=SimpleNamespace(
            compose_prompt=lambda *, base_prompt, skill_prompt: f"COMPOSED::{base_prompt}::{skill_prompt}"
        ),
        tool_capability_provider=SimpleNamespace(
            resolve_effective_tools=lambda *, agent_tools, skill: ["builtin:docs_read"]
        ),
    )
    agent = SimpleNamespace(
        name="Skill Agent",
        system_prompt="Persona prompt.",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read", "builtin:exec"],
    )

    result = chat_prompting.assemble_runtime_prompt(
        agent_config=agent,
        request_system_prompt=None,
        request_message="plan this release",
        provider=None,
        model_name=None,
        selected_skill_spec=selected_skill,
        always_skill_specs=[],
        summary_block=None,
        feature_flags={"skill_runtime_enabled": True},
        skill_registry=SimpleNamespace(get_full_skill=lambda *_args, **_kwargs: selected_skill),
        markdown_skill_adapter=fake_markdown_adapter,
        skill_policy_gate=SimpleNamespace(check_tool_intersection=lambda *_args, **_kwargs: []),
        build_scope_summary_block=lambda _agent: (None, 0),
        runtime_seams=runtime_seams,
    )

    assert result.system_prompt.startswith("COMPOSED::Persona prompt.::[Active Skill: planner]\nSkill prompt.")
    assert "### Additional Instructions\nFollow planner rules." in result.system_prompt
    assert result.final_tools_list == ["builtin:docs_read"]
