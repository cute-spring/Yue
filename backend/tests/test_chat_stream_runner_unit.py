import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.chat_stream_runner import (
    PromptRuntimeDeps,
    PreparedRuntime,
    PromptPreparation,
    RetryRuntimeDeps,
    StreamRunnerDeps,
    _create_stream_runtime,
    _finalize_stream_run,
    _handle_tool_call_mismatch_retry,
    _prepare_prompt_runtime,
)
from app.api.chat_tool_events import ToolEventTracker


def _make_deps() -> StreamRunnerDeps:
    return StreamRunnerDeps(
        logger=MagicMock(),
        agent_store=MagicMock(),
        tool_registry=MagicMock(),
        fetch_ollama_models=MagicMock(),
        get_model=MagicMock(),
        chat_service=MagicMock(),
        config_service=MagicMock(),
        build_system_prompt=MagicMock(),
        get_parser=MagicMock(),
        calculate_usage=MagicMock(),
        handle_llm_exception=MagicMock(side_effect=lambda err: str(err)),
        prompt=PromptRuntimeDeps(
            skill_registry=MagicMock(),
            skill_action_execution_service=MagicMock(),
            markdown_skill_adapter=MagicMock(),
            skill_policy_gate=MagicMock(),
            assemble_runtime_prompt=MagicMock(),
            build_scope_summary_block=MagicMock(),
            emit_skill_effectiveness_event=MagicMock(),
            resolve_skill_runtime_state=MagicMock(),
            action_preflight_message_builder=MagicMock(return_value="preflight summary"),
            action_approval_message_builder=MagicMock(return_value="approval summary"),
            action_execution_message_builder=MagicMock(return_value="execution summary"),
        ),
        retry=RetryRuntimeDeps(
            resolve_retry_targets=MagicMock(),
            build_tool_call_retry_event=MagicMock(),
            build_tool_call_retry_success_event=MagicMock(),
            build_tool_call_retry_failed_event=MagicMock(),
            build_tool_call_mismatch_event=MagicMock(),
            build_tool_call_mismatch_message=MagicMock(),
        ),
        collect_tool_names=MagicMock(),
        patch_model_settings=MagicMock(side_effect=lambda value: value),
        build_agent_deps=MagicMock(),
        ensure_ollama_model_available=MagicMock(),
        format_citations_suffix=MagicMock(),
        append_continue_message_if_needed=MagicMock(),
        append_citation_suffix_if_needed=MagicMock(),
        persist_assistant_message=MagicMock(),
        should_handle_tool_call_mismatch=MagicMock(),
        tool_event_tracker_cls=MagicMock(),
        normalize_finished_ts=MagicMock(side_effect=lambda value: value),
        serialize_sse_payload=lambda payload: payload,
        iso_utc_now=lambda: "2026-03-22T00:00:00Z",
        resolve_reasoning_state=MagicMock(),
        build_runtime_meta_payload=MagicMock(),
        run_agent_stream=MagicMock(),
        refine_title_once_fn=MagicMock(),
        build_chat_response_log_payload=MagicMock(return_value={"ok": True}),
        safe_json_log=MagicMock(return_value='{"ok": true}'),
        env_flag=MagicMock(return_value=False),
        env_flag_with_fallback=MagicMock(return_value=False),
        agent_cls=MagicMock(),
        usage_limits_cls=MagicMock(),
    )


def _make_request(**overrides):
    base = {
        "message": "hello",
        "provider": None,
        "model": None,
        "model_role": None,
        "system_prompt": "system",
        "agent_id": "agent-1",
        "requested_skill": None,
        "requested_action": None,
        "requested_action_arguments": None,
        "requested_action_approved": None,
        "requested_action_approval_token": None,
        "deep_thinking_enabled": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_create_stream_runtime_sets_expected_context_and_tracker():
    deps = _make_deps()
    deps.config_service.get_feature_flags.return_value = {
        "transparency_event_v2_enabled": True,
        "transparency_turn_binding_enabled": False,
        "reasoning_display_gated_enabled": True,
    }
    tracker = MagicMock()
    deps.tool_event_tracker_cls.return_value = tracker
    request = _make_request(provider="openai", model="gpt-4o")

    ctx, metrics, emitter, created_tracker = _create_stream_runtime(
        chat_id="chat-1",
        request=request,
        history=["h1"],
        validated_images=["img1"],
        deps=deps,
    )

    assert ctx.chat_id == "chat-1"
    assert ctx.history == ["h1"]
    assert ctx.validated_images == ["img1"]
    assert ctx.provider == "openai"
    assert ctx.model_name == "gpt-4o"
    assert ctx.request_id.startswith("req_")
    assert metrics.total_tokens == 0
    assert created_tracker is tracker
    assert emitter.run_id.startswith("run_")
    deps.tool_event_tracker_cls.assert_called_once()


def test_prepare_prompt_runtime_emits_events_and_updates_context():
    async def run_test():
        deps = _make_deps()
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": SimpleNamespace(name="skill-a"),
            "always_skill_specs": [],
            "selection_reason_code": "skill_selected",
            "selection_source": "explicit",
            "selection_score": 9,
            "visible_skill_count": 2,
            "available_skill_count": 2,
            "always_injected_count": 1,
            "selected_group_ids": ["group-1"],
            "resolved_skill_count": 3,
            "summary_block": "summary",
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=SimpleNamespace(name="skill-a"),
            provider="deepseek",
            model_name="deepseek-chat",
            system_prompt="assembled prompt",
            final_tools_list=["docs_read"],
            always_injected_count=2,
            emitted_event={"event": "skill.selected"},
            summary_injected=True,
            scope_summary_injected=True,
            effective_scope_count=4,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = "skill_effectiveness_event"

        tracker = MagicMock()
        deps.tool_event_tracker_cls.return_value = tracker
        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request()
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0]["event"] == "skill.selected"
        assert outputs[1] == "skill_effectiveness_event"
        assert isinstance(outputs[2], PromptPreparation)
        assert outputs[2].final_tools_list == ["docs_read"]
        assert ctx.provider == "deepseek"
        assert ctx.model_name == "deepseek-chat"
        assert ctx.system_prompt == "assembled prompt"
        deps.chat_service.add_action_event.assert_called_once()
        action_event = deps.chat_service.add_action_event.call_args.args[1]
        assert action_event["event"] == "chat.request.snapshot"
        assert action_event["request_id"] == ctx.request_id
        assert action_event["snapshot"]["system_prompt"] == "assembled prompt"
        assert action_event["snapshot"]["tool_context"]["enabled_tools"] == ["docs_read"]

    asyncio.run(run_test())


def test_prepare_prompt_runtime_snapshot_persistence_is_fail_open():
    async def run_test():
        deps = _make_deps()
        deps.chat_service.add_action_event.side_effect = RuntimeError("db down")
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": None,
            "always_skill_specs": [],
            "selection_reason_code": "none",
            "selection_source": "none",
            "selection_score": 0,
            "visible_skill_count": 0,
            "available_skill_count": 0,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 0,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=None,
            provider="openai",
            model_name="gpt-4o",
            system_prompt="assembled prompt",
            final_tools_list=[],
            always_injected_count=0,
            emitted_event=None,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request()
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0] == {"event": "skill_effectiveness"}
        assert isinstance(outputs[1], PromptPreparation)
        deps.logger.exception.assert_called_once()

    asyncio.run(run_test())


def test_prepare_prompt_runtime_applies_request_model_role_resolution():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_role.side_effect = (
            lambda role: {"provider": "deepseek", "model": "deepseek-reasoner"} if role == "reasoning" else None
        )
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": None,
            "always_skill_specs": [],
            "selection_reason_code": "none",
            "selection_source": "none",
            "selection_score": 0,
            "visible_skill_count": 0,
            "available_skill_count": 0,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 0,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=None,
            provider="openai",
            model_name="gpt-4o",
            system_prompt="assembled prompt",
            final_tools_list=[],
            always_injected_count=0,
            emitted_event=None,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}

        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request(agent_id=None, provider=None, model=None, model_role="reasoning")
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert isinstance(outputs[1], PromptPreparation)
        assert ctx.provider == "deepseek"
        assert ctx.model_name == "deepseek-reasoner"

    asyncio.run(run_test())


def test_prepare_prompt_runtime_respects_request_provider_model_override():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_role.return_value = {"provider": "openai", "model": "gpt-4o-mini"}
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": None,
            "always_skill_specs": [],
            "selection_reason_code": "none",
            "selection_source": "none",
            "selection_score": 0,
            "visible_skill_count": 0,
            "available_skill_count": 0,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 0,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=None,
            provider="openai",
            model_name="gpt-4o",
            system_prompt="assembled prompt",
            final_tools_list=[],
            always_injected_count=0,
            emitted_event=None,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request(provider="openai", model="gpt-4o", model_role="reasoning")
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert isinstance(outputs[1], PromptPreparation)
        assert ctx.provider == "openai"
        assert ctx.model_name == "gpt-4o"

    asyncio.run(run_test())


def test_prepare_prompt_runtime_force_direct_agent_policy_beats_agent_role():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_role.side_effect = (
            lambda role: {"provider": "deepseek", "model": "deepseek-reasoner"} if role == "reasoning" else None
        )
        deps.agent_store.get_agent.return_value = SimpleNamespace(
            provider="anthropic",
            model="claude-3-7-sonnet",
            model_policy="force_direct",
            model_role="reasoning",
            enabled_tools=["builtin:docs_read"],
            system_prompt="agent prompt",
            doc_roots=[],
            skill_mode="off",
        )
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": None,
            "always_skill_specs": [],
            "selection_reason_code": "none",
            "selection_source": "none",
            "selection_score": 0,
            "visible_skill_count": 0,
            "available_skill_count": 0,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 0,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=None,
            provider="openai",
            model_name="gpt-4o",
            system_prompt="assembled prompt",
            final_tools_list=["builtin:docs_read"],
            always_injected_count=0,
            emitted_event=None,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request(agent_id="agent-1", provider=None, model=None)
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert isinstance(outputs[1], PromptPreparation)
        assert ctx.provider == "anthropic"
        assert ctx.model_name == "claude-3-7-sonnet"

    asyncio.run(run_test())


def test_prepare_prompt_runtime_uses_agent_tier_and_records_model_resolution_meta():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_tier.side_effect = (
            lambda tier: {"provider": "anthropic", "model": "claude-3-7-sonnet", "tier": tier}
            if tier == "heavy"
            else None
        )
        deps.config_service.resolve_model_role.side_effect = (
            lambda role: {"provider": "deepseek", "model": "deepseek-reasoner"} if role == "reasoning" else None
        )
        deps.agent_store.get_agent.return_value = SimpleNamespace(
            provider="openai",
            model="gpt-4o-mini",
            model_selection_mode="tier",
            model_tier="heavy",
            model_policy="prefer_role",
            model_role="reasoning",
            enabled_tools=[],
            system_prompt="agent prompt",
            doc_roots=[],
            skill_mode="off",
        )
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": None,
            "always_skill_specs": [],
            "selection_reason_code": "none",
            "selection_source": "none",
            "selection_score": 0,
            "visible_skill_count": 0,
            "available_skill_count": 0,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 0,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=None,
            provider="openai",
            model_name="gpt-4o-mini",
            system_prompt="assembled prompt",
            final_tools_list=[],
            always_injected_count=0,
            emitted_event=None,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request(agent_id="agent-1", provider=None, model=None)
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert isinstance(outputs[1], PromptPreparation)
        assert ctx.provider == "anthropic"
        assert ctx.model_name == "claude-3-7-sonnet"
        assert ctx.model_resolution["tier"] == "heavy"
        assert ctx.model_resolution["resolution_source"] == "agent_tier"

    asyncio.run(run_test())


def test_prepare_runtime_dependencies_runtime_meta_includes_tier_resolution():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_tier.side_effect = (
            lambda tier: {"provider": "anthropic", "model": "claude-3-7-sonnet", "tier": tier}
            if tier == "heavy"
            else None
        )
        deps.agent_store.get_agent.return_value = SimpleNamespace(
            provider="openai",
            model="gpt-4o-mini",
            model_selection_mode="tier",
            model_tier="heavy",
            model_policy="prefer_role",
            model_role=None,
            enabled_tools=[],
            system_prompt="agent prompt",
            doc_roots=[],
            skill_mode="off",
        )
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": None,
            "always_skill_specs": [],
            "selection_reason_code": "none",
            "selection_source": "none",
            "selection_score": 0,
            "visible_skill_count": 0,
            "available_skill_count": 0,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 0,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=None,
            provider="openai",
            model_name="gpt-4o-mini",
            system_prompt="assembled prompt",
            final_tools_list=[],
            always_injected_count=0,
            emitted_event=None,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.config_service.get_feature_flags.return_value = {}
        deps.tool_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        deps.collect_tool_names.return_value = []
        deps.config_service.get_model_capabilities.return_value = []
        deps.resolve_reasoning_state.return_value = (False, "DEEP_THINKING_DISABLED")
        deps.build_system_prompt.return_value = "assembled prompt"
        deps.get_model.return_value = object()
        deps.build_agent_deps.return_value = {}
        deps.ensure_ollama_model_available = AsyncMock(return_value=("claude-3-7-sonnet", None))
        deps.config_service.get_model_settings.return_value = {}
        deps.config_service.get_usage_limits.return_value = {"request_limit": 12, "tool_calls_limit": 8}
        multimodal_service = MagicMock()
        multimodal_service.decide_vision.return_value = {
            "supports_vision": False,
            "vision_enabled": False,
            "fallback_mode": "disabled",
        }
        request = _make_request(agent_id="agent-1", provider=None, model=None)
        ctx, metrics, emitter, tool_tracker = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        from app.api.chat_stream_runner import _prepare_runtime_dependencies

        async for step in _prepare_runtime_dependencies(
            ctx=ctx,
            metrics=metrics,
            emitter=emitter,
            tool_tracker=tool_tracker,
            multimodal_service=multimodal_service,
            validated_images=[],
            request=request,
            deps=deps,
        ):
            outputs.append(step)
            if isinstance(step, PreparedRuntime):
                break

        meta_call = deps.build_runtime_meta_payload.call_args
        assert meta_call is not None
        assert meta_call.kwargs["model_resolution"]["tier"] == "heavy"
        assert meta_call.kwargs["model_resolution"]["resolution_source"] == "agent_tier"
        assert outputs[0]["event"] == "skill_effectiveness"

    asyncio.run(run_test())


def test_prepare_prompt_runtime_reassembles_skill_prompt_with_resolved_model_role():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_role.side_effect = (
            lambda role: {"provider": "deepseek", "model": "deepseek-reasoner"} if role == "reasoning" else None
        )
        deps.agent_store.get_agent.return_value = SimpleNamespace(
            provider="openai",
            model="gpt-4o-mini",
            model_policy="prefer_role",
            model_role=None,
            enabled_tools=["builtin:docs_read"],
            system_prompt="agent prompt",
            doc_roots=[],
            skill_mode="manual",
        )
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": SimpleNamespace(name="skill-a", version="1.0.0"),
            "always_skill_specs": [SimpleNamespace(name="always-a", version="1.0.0")],
            "selection_reason_code": "skill_selected",
            "selection_source": "explicit",
            "selection_score": 9,
            "visible_skill_count": 1,
            "available_skill_count": 1,
            "always_injected_count": 1,
            "selected_group_ids": ["group-1"],
            "resolved_skill_count": 1,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.side_effect = [
            SimpleNamespace(
                selected_skill_spec=SimpleNamespace(name="skill-a", version="1.0.0"),
                provider="openai",
                model_name="gpt-4o-mini",
                system_prompt="assembled with default model",
                final_tools_list=["builtin:docs_read"],
                always_injected_count=1,
                emitted_event=None,
                summary_injected=False,
                scope_summary_injected=False,
                effective_scope_count=0,
            ),
            SimpleNamespace(
                selected_skill_spec=SimpleNamespace(name="skill-a", version="1.0.0"),
                provider="deepseek",
                model_name="deepseek-reasoner",
                system_prompt="assembled with resolved model",
                final_tools_list=["builtin:docs_read"],
                always_injected_count=1,
                emitted_event=None,
                summary_injected=False,
                scope_summary_injected=False,
                effective_scope_count=0,
            ),
        ]
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.config_service.get_feature_flags.return_value = {}
        request = _make_request(agent_id="agent-1", model_role="reasoning")
        ctx, _, emitter, _ = _create_stream_runtime(
            chat_id="chat-1",
            request=request,
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        async for item in _prepare_prompt_runtime(
            ctx=ctx,
            emitter=emitter,
            request=request,
            deps=deps,
        ):
            outputs.append(item)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert isinstance(outputs[1], PromptPreparation)
        assert ctx.provider == "deepseek"
        assert ctx.model_name == "deepseek-reasoner"
        assert ctx.system_prompt == "assembled with resolved model"
        assert deps.prompt.assemble_runtime_prompt.call_count == 2
        first_call = deps.prompt.assemble_runtime_prompt.call_args_list[0]
        second_call = deps.prompt.assemble_runtime_prompt.call_args_list[1]
        assert first_call.kwargs["provider"] is None
        assert first_call.kwargs["model_name"] is None
        assert second_call.kwargs["provider"] == "deepseek"
        assert second_call.kwargs["model_name"] == "deepseek-reasoner"

    asyncio.run(run_test())


def test_prepare_runtime_dependencies_requested_action_resume_after_approval():
    async def run_test():
        deps = _make_deps()
        deps.tool_event_tracker_cls = ToolEventTracker
        deps.build_agent_deps.return_value = {}
        deps.config_service.get_feature_flags.return_value = {}
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": SimpleNamespace(name="skill-a", version="1.0.0"),
            "always_skill_specs": [],
            "selection_reason_code": "skill_selected",
            "selection_source": "explicit",
            "selection_score": 9,
            "visible_skill_count": 2,
            "available_skill_count": 2,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 1,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=SimpleNamespace(name="skill-a", version="1.0.0"),
            provider="openai",
            model_name="gpt-4o",
            system_prompt="assembled prompt",
            final_tools_list=["builtin:exec"],
            always_injected_count=0,
            selected_group_ids=[],
            resolved_skill_count=1,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
            emitted_event=None,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        invocation = SimpleNamespace(
            action_id="generate",
            skill_name="skill-a",
            skill_version="1.0.0",
            mapped_tool="builtin:exec",
        )
        deps.prompt.skill_action_execution_service.preflight.return_value = SimpleNamespace(
            event_payloads=[
                {"event": "skill.action.preflight", "action_id": "generate", "lifecycle_phase": "preflight", "lifecycle_status": "preflight_evaluated"},
                {"event": "skill.action.result", "action_id": "generate", "status": "approval_required", "lifecycle_phase": "preflight", "lifecycle_status": "preflight_approval_required"},
            ],
            lifecycle_status="preflight_approval_required",
            invocation=invocation,
            request_id=None,
            metadata={"validated_arguments": {}},
        )
        deps.prompt.skill_action_execution_service.build_approval_result.return_value = SimpleNamespace(
            event_payloads=[
                {"event": "skill.action.approval", "action_id": "generate", "lifecycle_phase": "approval", "lifecycle_status": "approved"}
            ],
            lifecycle_status="approved",
            approval_token="approval:skill-a:1.0.0:generate:manual",
        )
        deps.prompt.skill_action_execution_service.build_transition_result.side_effect = (
            lambda *, invocation, status, request_id=None, lifecycle_phase="execution", lifecycle_status=None, metadata=None:
                SimpleNamespace(
                    event_payloads=[
                        {
                            "event": "skill.action.result",
                            "action_id": invocation.action_id,
                            "status": status,
                            "lifecycle_phase": lifecycle_phase,
                            "lifecycle_status": lifecycle_status or status,
                        }
                    ],
                    lifecycle_status=lifecycle_status or status,
                    metadata=metadata or {},
                    invocation=invocation,
                )
        )
        fake_tool = SimpleNamespace(
            name="exec",
            validate_params=lambda args: args,
            execute=AsyncMock(return_value="tool execution output"),
        )
        deps.tool_registry.get_tools_for_agent = AsyncMock(return_value=[fake_tool])
        ctx, metrics, emitter, tool_tracker = _create_stream_runtime(
            chat_id="chat-1",
            request=_make_request(
                requested_action="generate",
                requested_action_arguments={"command": "pwd", "cwd": "/workspace"},
                requested_action_approved=True,
                requested_action_approval_token="approval:skill-a:1.0.0:generate:manual",
            ),
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        from app.api.chat_stream_runner import _prepare_runtime_dependencies

        async for step in _prepare_runtime_dependencies(
            ctx=ctx,
            metrics=metrics,
            emitter=emitter,
            tool_tracker=tool_tracker,
            multimodal_service=MagicMock(),
            validated_images=[],
            request=_make_request(
                requested_action="generate",
                requested_action_arguments={"command": "pwd", "cwd": "/workspace"},
                requested_action_approved=True,
                requested_action_approval_token="approval:skill-a:1.0.0:generate:manual",
            ),
            deps=deps,
        ):
            outputs.append(step)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert outputs[1]["event"] == "skill.action.preflight"
        assert outputs[2]["event"] == "skill.action.result"
        assert outputs[3]["event"] == "skill.action.approval"
        assert outputs[4]["lifecycle_status"] == "queued"
        assert outputs[5]["lifecycle_status"] == "running"
        queued_call = deps.prompt.skill_action_execution_service.build_transition_result.call_args_list[0]
        assert queued_call.kwargs["metadata"]["tool_args"] == {"command": "pwd", "cwd": "/workspace"}
        assert any(isinstance(item, dict) and item.get("lifecycle_status") == "succeeded" for item in outputs)
        assert any(isinstance(item, dict) and item.get("content") == "preflight summary" for item in outputs)
        assert any(isinstance(item, dict) and item.get("content") == "approval summary" for item in outputs)
        assert any(isinstance(item, dict) and item.get("content") == "execution summary" for item in outputs)
        assert any(isinstance(item, dict) and "tool execution output" in str(item.get("content")) for item in outputs)

    asyncio.run(run_test())


def test_prepare_runtime_dependencies_requested_action_uses_resolved_request_model_role():
    async def run_test():
        deps = _make_deps()
        deps.config_service.resolve_model_role.side_effect = (
            lambda role: {"provider": "deepseek", "model": "deepseek-reasoner"} if role == "reasoning" else None
        )
        deps.build_agent_deps.return_value = {}
        deps.config_service.get_feature_flags.return_value = {}
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": SimpleNamespace(name="skill-a", version="1.0.0"),
            "always_skill_specs": [],
            "selection_reason_code": "skill_selected",
            "selection_source": "explicit",
            "selection_score": 9,
            "visible_skill_count": 1,
            "available_skill_count": 1,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 1,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.side_effect = [
            SimpleNamespace(
                selected_skill_spec=SimpleNamespace(name="skill-a", version="1.0.0"),
                provider="openai",
                model_name="gpt-4o-mini",
                system_prompt="assembled prompt",
                final_tools_list=["builtin:exec"],
                always_injected_count=0,
                selected_group_ids=[],
                resolved_skill_count=1,
                summary_injected=False,
                scope_summary_injected=False,
                effective_scope_count=0,
                emitted_event=None,
            ),
            SimpleNamespace(
                selected_skill_spec=SimpleNamespace(name="skill-a", version="1.0.0"),
                provider="deepseek",
                model_name="deepseek-reasoner",
                system_prompt="assembled prompt",
                final_tools_list=["builtin:exec"],
                always_injected_count=0,
                selected_group_ids=[],
                resolved_skill_count=1,
                summary_injected=False,
                scope_summary_injected=False,
                effective_scope_count=0,
                emitted_event=None,
            ),
        ]
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.prompt.skill_action_execution_service.preflight.return_value = SimpleNamespace(
            event_payloads=[],
            lifecycle_status="preflight_ready",
            invocation=SimpleNamespace(
                action_id="generate",
                skill_name="skill-a",
                skill_version="1.0.0",
                mapped_tool="builtin:exec",
            ),
            request_id="req-action",
            metadata={"validated_arguments": {"command": "pwd"}},
        )
        deps.prompt.skill_action_execution_service.build_transition_result.side_effect = (
            lambda **kwargs: SimpleNamespace(
                event_payloads=[],
                lifecycle_status=kwargs.get("lifecycle_status"),
                metadata=kwargs.get("metadata") or {},
                invocation=kwargs["invocation"],
            )
        )
        deps.tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

        ctx, metrics, emitter, tool_tracker = _create_stream_runtime(
            chat_id="chat-1",
            request=_make_request(
                requested_action="generate",
                requested_action_arguments={"command": "pwd"},
                model_role="reasoning",
            ),
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        from app.api.chat_stream_runner import _prepare_runtime_dependencies

        async for step in _prepare_runtime_dependencies(
            ctx=ctx,
            metrics=metrics,
            emitter=emitter,
            tool_tracker=tool_tracker,
            multimodal_service=MagicMock(),
            validated_images=[],
            request=_make_request(
                requested_action="generate",
                requested_action_arguments={"command": "pwd"},
                model_role="reasoning",
            ),
            deps=deps,
        ):
            outputs.append(step)

        invocation_request = deps.prompt.skill_action_execution_service.preflight.call_args.args[0]
        assert invocation_request.invocation.provider == "deepseek"
        assert invocation_request.invocation.model_name == "deepseek-reasoner"
        assert outputs[0]["event"] == "skill_effectiveness"

    asyncio.run(run_test())


def test_prepare_runtime_dependencies_short_circuits_for_requested_action():
    async def run_test():
        deps = _make_deps()
        deps.prompt.resolve_skill_runtime_state.return_value = {
            "selected_skill_spec": SimpleNamespace(name="skill-a", version="1.0.0"),
            "always_skill_specs": [],
            "selection_reason_code": "skill_selected",
            "selection_source": "explicit",
            "selection_score": 9,
            "visible_skill_count": 2,
            "available_skill_count": 2,
            "always_injected_count": 0,
            "selected_group_ids": [],
            "resolved_skill_count": 1,
            "summary_block": None,
        }
        deps.prompt.assemble_runtime_prompt.return_value = SimpleNamespace(
            selected_skill_spec=SimpleNamespace(name="skill-a", version="1.0.0"),
            provider="openai",
            model_name="gpt-4o",
            system_prompt="assembled prompt",
            final_tools_list=["builtin:exec"],
            always_injected_count=0,
            selected_group_ids=[],
            resolved_skill_count=1,
            summary_injected=False,
            scope_summary_injected=False,
            effective_scope_count=0,
            emitted_event=None,
        )
        deps.prompt.emit_skill_effectiveness_event.return_value = {"event": "skill_effectiveness"}
        deps.prompt.skill_action_execution_service.preflight.return_value = SimpleNamespace(
            event_payloads=[
                {"event": "skill.action.preflight", "action_id": "generate", "lifecycle_phase": "preflight", "lifecycle_status": "preflight_evaluated"},
                {"event": "skill.action.result", "action_id": "generate", "status": "approval_required", "lifecycle_phase": "preflight", "lifecycle_status": "preflight_approval_required"},
            ],
            lifecycle_status="preflight_approval_required",
        )
        deps.prompt.skill_action_execution_service.build_stub_execution_results.return_value = [
            SimpleNamespace(
                event_payloads=[
                    {"event": "skill.action.result", "action_id": "generate", "status": "awaiting_approval", "lifecycle_phase": "execution", "lifecycle_status": "awaiting_approval"}
                ]
            )
        ]
        ctx, metrics, emitter, tool_tracker = _create_stream_runtime(
            chat_id="chat-1",
            request=_make_request(requested_action="generate"),
            history=[],
            validated_images=[],
            deps=deps,
        )

        outputs = []
        from app.api.chat_stream_runner import _prepare_runtime_dependencies

        async for step in _prepare_runtime_dependencies(
            ctx=ctx,
            metrics=metrics,
            emitter=emitter,
            tool_tracker=tool_tracker,
            multimodal_service=MagicMock(),
            validated_images=[],
            request=_make_request(requested_action="generate"),
            deps=deps,
        ):
            outputs.append(step)

        assert outputs[0]["event"] == "skill_effectiveness"
        assert outputs[1]["event"] == "skill.action.preflight"
        assert outputs[2]["event"] == "skill.action.result"
        assert outputs[2]["lifecycle_status"] == "preflight_approval_required"
        assert outputs[3]["event"] == "skill.action.result"
        assert outputs[3]["lifecycle_status"] == "awaiting_approval"
        assert outputs[4]["content"] == "preflight summary"
        assert outputs[5]["content"] == "execution summary"
        deps.tool_registry.get_pydantic_ai_tools_for_agent.assert_not_called()
        deps.get_model.assert_not_called()

    asyncio.run(run_test())


def test_handle_tool_call_mismatch_retry_emits_retry_and_success():
    async def run_test():
        deps = _make_deps()
        deps.retry.resolve_retry_targets.return_value = [SimpleNamespace(provider="deepseek", model_name="deepseek-chat")]
        deps.retry.build_tool_call_retry_event.return_value = {"event": "tool_call_retry"}
        deps.retry.build_tool_call_retry_success_event.return_value = {"event": "tool_call_retry_success"}

        async def fake_run_agent_stream(**kwargs):
            kwargs["result_holder"]["result"] = SimpleNamespace(
                response=SimpleNamespace(finish_reason="stop")
            )
            yield "retry-stream-payload"

        deps.run_agent_stream = fake_run_agent_stream

        request = _make_request()
        ctx = SimpleNamespace(
            provider="openai",
            model_name="gpt-4o",
            system_prompt="system",
            history=[],
            deps={},
            tool_event_queue=asyncio.Queue(),
            stream_state=SimpleNamespace(full_response=""),
            usage_limits=None,
        )
        prepared = PreparedRuntime(
            emitter=SimpleNamespace(emit=lambda payload: payload),
            tool_tracker=SimpleNamespace(counts={"started": 0, "finished": 0}),
            tools=[],
            model=None,
            multimodal_service=SimpleNamespace(
                build_user_input=lambda **kwargs: {"input": kwargs["message"]}
            ),
            validated_images=[],
            request=request,
            model_capabilities=[],
            vision_enabled=False,
        )

        outputs = []
        async for item in _handle_tool_call_mismatch_retry(ctx=ctx, prepared=prepared, deps=deps):
            outputs.append(item)

        assert outputs[0]["event"] == "tool_call_retry"
        assert "retry-stream-payload" in outputs
        assert outputs[-1]["event"] == "tool_call_retry_success"

    asyncio.run(run_test())


def test_handle_tool_call_mismatch_retry_emits_mismatch_when_unresolved():
    async def run_test():
        deps = _make_deps()
        deps.retry.resolve_retry_targets.return_value = [SimpleNamespace(provider="deepseek", model_name="deepseek-chat")]
        deps.retry.build_tool_call_retry_event.return_value = {"event": "tool_call_retry"}
        deps.retry.build_tool_call_mismatch_event.return_value = {"event": "tool_call_mismatch"}
        deps.retry.build_tool_call_mismatch_message.return_value = "mismatch message"

        async def fake_run_agent_stream(**kwargs):
            kwargs["result_holder"]["result"] = SimpleNamespace(
                response=SimpleNamespace(finish_reason="tool_call")
            )
            if False:
                yield None

        deps.run_agent_stream = fake_run_agent_stream

        ctx = SimpleNamespace(
            provider="openai",
            model_name="gpt-4o",
            system_prompt="system",
            history=[],
            deps={},
            tool_event_queue=asyncio.Queue(),
            stream_state=SimpleNamespace(full_response=""),
            usage_limits=None,
        )
        prepared = PreparedRuntime(
            emitter=SimpleNamespace(emit=lambda payload: payload),
            tool_tracker=SimpleNamespace(counts={"started": 0, "finished": 0}),
            tools=[],
            model=None,
            multimodal_service=SimpleNamespace(build_user_input=lambda **kwargs: {"input": "x"}),
            validated_images=[],
            request=_make_request(),
            model_capabilities=[],
            vision_enabled=False,
        )

        outputs = []
        async for item in _handle_tool_call_mismatch_retry(ctx=ctx, prepared=prepared, deps=deps):
            outputs.append(item)

        assert outputs[-2]["event"] == "tool_call_mismatch"
        assert outputs[-1]["content"] == "mismatch message"
        assert ctx.stream_state.full_response == "mismatch message"

    asyncio.run(run_test())


def test_finalize_stream_run_persists_and_logs():
    deps = _make_deps()
    deps.persist_assistant_message.return_value = True
    deps.env_flag_with_fallback.return_value = True
    ctx = SimpleNamespace(
        chat_id="chat-1",
        stream_state=SimpleNamespace(full_response="answer"),
        assistant_turn_id="turn-1",
        run_id="run-1",
        turn_binding_enabled=True,
        provider="openai",
        model_name="gpt-4o",
        request=SimpleNamespace(deep_thinking_enabled=False),
    )
    metrics = SimpleNamespace(
        thought_duration=0.1,
        ttft=0.2,
        total_duration=1.0,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        finish_reason="stop",
        current_exception=None,
        supports_reasoning=False,
        reasoning_enabled=False,
        stream_error_message=None,
    )
    tool_tracker = SimpleNamespace(counts={"started": 1, "finished": 1})

    with patch("app.api.chat_stream_runner.asyncio.create_task") as mock_create_task:
        _finalize_stream_run(ctx=ctx, metrics=metrics, tool_tracker=tool_tracker, deps=deps)

    deps.persist_assistant_message.assert_called_once()
    mock_create_task.assert_called_once()
    deps.logger.info.assert_called_once()
