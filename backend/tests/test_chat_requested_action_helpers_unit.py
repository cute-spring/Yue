import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.chat_requested_action_flow import run_requested_action_flow
from app.api.chat_requested_action_adapter import build_requested_action_messages
from app.api.chat_requested_action_events import persist_action_lifecycle_events
from app.api.chat_requested_action_tools import (
    invoke_requested_action_platform_tool,
    resolve_requested_action_request_id,
    resolve_requested_action_tool_args,
)


def test_persist_action_lifecycle_events_envelopes_and_persists():
    lifecycle_results = [
        SimpleNamespace(event_payloads=[{"event": "skill.action.result", "status": "queued"}]),
        SimpleNamespace(event_payloads=[{"event": "skill.action.result", "status": "running"}]),
    ]
    ctx = SimpleNamespace(chat_id="chat-1", assistant_turn_id="turn-1", run_id="run-1")
    emitter = MagicMock()
    emitter.event_payload.side_effect = lambda payload: {"wrapped": payload}
    deps = SimpleNamespace(chat_service=MagicMock(), serialize_sse_payload=lambda payload: payload)

    payloads = persist_action_lifecycle_events(
        lifecycle_results=lifecycle_results,
        ctx=ctx,
        emitter=emitter,
        deps=deps,
    )

    assert payloads == [
        {"wrapped": {"event": "skill.action.result", "status": "queued"}},
        {"wrapped": {"event": "skill.action.result", "status": "running"}},
    ]
    assert deps.chat_service.add_action_event.call_count == 2


def test_resolve_requested_action_request_id_prefers_approval_token_suffix():
    request = SimpleNamespace(requested_action_approval_token="approval:skill-a:1.0.0:generate:req-123")
    assert resolve_requested_action_request_id(request) == "req-123"


def test_resolve_requested_action_tool_args_prefers_validated_arguments():
    request = SimpleNamespace(requested_action_arguments={"command": "pwd"})
    preflight_result = SimpleNamespace(metadata={"validated_arguments": {"command": "ls", "cwd": "/"}})
    assert resolve_requested_action_tool_args(preflight_result, request) == {"command": "ls", "cwd": "/"}


def test_resolve_requested_action_tool_args_merges_browser_resolved_context_when_missing():
    request = SimpleNamespace(requested_action_arguments={"text": "hello"})
    preflight_result = SimpleNamespace(
        metadata={
            "tool_family": "agent_browser",
            "validated_arguments": {"text": "hello"},
            "browser_continuity_resolution": {
                "continuity_status": "resolved",
                "resolved_context": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:2",
                },
            },
        }
    )

    assert resolve_requested_action_tool_args(preflight_result, request) == {
        "text": "hello",
        "session_id": "session-1",
        "tab_id": "tab-1",
        "element_ref": "snapshot:browser_snapshot#node:2",
    }


def test_resolve_requested_action_tool_args_preserves_explicit_browser_args_over_resolved_context():
    request = SimpleNamespace(requested_action_arguments={"text": "hello"})
    preflight_result = SimpleNamespace(
        metadata={
            "tool_family": "agent_browser",
            "validated_arguments": {
                "text": "hello",
                "session_id": "session-explicit",
                "tab_id": "tab-explicit",
                "element_ref": "snapshot:browser_snapshot#node:9",
            },
            "browser_continuity_resolution": {
                "continuity_status": "resolved",
                "resolved_context": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:2",
                },
            },
        }
    )

    assert resolve_requested_action_tool_args(preflight_result, request) == {
        "text": "hello",
        "session_id": "session-explicit",
        "tab_id": "tab-explicit",
        "element_ref": "snapshot:browser_snapshot#node:9",
    }


def test_build_requested_action_messages_appends_artifact_image_summary_for_screenshot():
    preflight_result = SimpleNamespace(
        invocation=SimpleNamespace(mapped_tool="builtin:browser_screenshot"),
    )
    prompt_deps = SimpleNamespace(
        action_preflight_message_builder=MagicMock(return_value="preflight summary"),
        action_approval_message_builder=MagicMock(return_value="approval summary"),
        action_execution_message_builder=MagicMock(return_value="execution summary"),
    )

    messages = build_requested_action_messages(
        preflight_result=preflight_result,
        approval_result=None,
        lifecycle_results=[],
        prompt_deps=prompt_deps,
        tool_result_payload='{"filename":"browser-shot.png","download_markdown":"[browser-shot.png](/exports/browser-shot.png)","download_url":"/exports/browser-shot.png","artifact":{"kind":"screenshot"}}',
        tool_error_payload=None,
    )

    assert messages == [
        "preflight summary",
        "[Tool Result] `builtin:browser_screenshot` returned:\n"
        '{"filename":"browser-shot.png","download_markdown":"[browser-shot.png](/exports/browser-shot.png)","download_url":"/exports/browser-shot.png","artifact":{"kind":"screenshot"}}',
        "Screenshot ready:\n![browser-shot.png](/exports/browser-shot.png)",
    ]


@pytest.mark.asyncio
async def test_invoke_requested_action_platform_tool_executes_matching_builtin_tool():
    selected_tool = SimpleNamespace(
        name="exec",
        validate_params=MagicMock(side_effect=lambda payload: {"validated": payload}),
        execute=AsyncMock(return_value="ok"),
    )
    deps = SimpleNamespace(
        tool_registry=SimpleNamespace(
            get_tools_for_agent=AsyncMock(return_value=[selected_tool])
        )
    )
    tool_tracker = SimpleNamespace(on_tool_event=AsyncMock())
    ctx = SimpleNamespace(deps={"trace": "deps"}, run_id="run-1", assistant_turn_id="turn-1")

    result = await invoke_requested_action_platform_tool(
        ctx=ctx,
        deps=deps,
        tool_tracker=tool_tracker,
        agent_id="agent-1",
        mapped_tool="builtin:exec",
        enabled_tools=["builtin:exec"],
        arguments={"command": "pwd"},
    )

    assert result == "ok"
    selected_tool.validate_params.assert_called_once_with({"command": "pwd"})
    selected_tool.execute.assert_awaited_once()
    assert tool_tracker.on_tool_event.await_count == 2


@pytest.mark.asyncio
async def test_invoke_requested_action_platform_tool_raises_for_unavailable_tool():
    deps = SimpleNamespace(
        tool_registry=SimpleNamespace(
            get_tools_for_agent=AsyncMock(return_value=[])
        )
    )
    tool_tracker = SimpleNamespace(on_tool_event=AsyncMock())
    ctx = SimpleNamespace(deps={}, run_id="run-1", assistant_turn_id="turn-1")

    with pytest.raises(ValueError, match="Requested action tool is unavailable"):
        await invoke_requested_action_platform_tool(
            ctx=ctx,
            deps=deps,
            tool_tracker=tool_tracker,
            agent_id="agent-1",
            mapped_tool="builtin:exec",
            enabled_tools=["builtin:exec"],
            arguments={"command": "pwd"},
        )


@pytest.mark.asyncio
async def test_run_requested_action_flow_hydrates_browser_tool_args_from_resolved_context():
    invocation = SimpleNamespace(
        action_id="click_element",
        skill_name="browser-operator",
        skill_version="1.0.0",
        mapped_tool="builtin:browser_click",
    )
    preflight_result = SimpleNamespace(
        event_payloads=[
            {"event": "skill.action.preflight", "action_id": "click_element", "lifecycle_phase": "preflight", "lifecycle_status": "preflight_evaluated"},
            {"event": "skill.action.result", "action_id": "click_element", "status": "approval_required", "lifecycle_phase": "preflight", "lifecycle_status": "preflight_approval_required"},
        ],
        lifecycle_status="preflight_approval_required",
        invocation=invocation,
        request_id="req-browser",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "binding_source": "snapshot:browser_snapshot",
            },
            "browser_continuity_resolution": {
                "continuity_status": "resolved",
                "resolved_context": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                },
            },
            "browser_continuity_resolver": {
                "resolver_id": "explicit_context",
                "status": "resolved",
                "resolved": True,
            },
        },
    )
    approval_result = SimpleNamespace(
        event_payloads=[
            {"event": "skill.action.approval", "action_id": "click_element", "lifecycle_phase": "approval", "lifecycle_status": "approved"}
        ],
        lifecycle_status="approved",
        approval_token="approval:browser-operator:1.0.0:click_element:req-browser",
    )
    transition_calls = []

    def build_transition_result(**kwargs):
        transition_calls.append(kwargs)
        lifecycle_status = kwargs.get("lifecycle_status") or kwargs.get("status")
        return SimpleNamespace(
            event_payloads=[
                {
                    "event": "skill.action.result",
                    "action_id": kwargs["invocation"].action_id,
                    "status": kwargs["status"],
                    "lifecycle_phase": kwargs.get("lifecycle_phase", "execution"),
                    "lifecycle_status": lifecycle_status,
                    "metadata": kwargs.get("metadata", {}),
                }
            ],
            lifecycle_status=lifecycle_status,
            metadata=kwargs.get("metadata", {}),
            invocation=kwargs["invocation"],
            request_id=kwargs.get("request_id"),
        )

    service = SimpleNamespace(
        preflight=MagicMock(return_value=preflight_result),
        build_approval_result=MagicMock(return_value=approval_result),
        build_transition_result=MagicMock(side_effect=build_transition_result),
        build_stub_execution_results=MagicMock(return_value=[]),
    )
    selected_tool = SimpleNamespace(
        name="browser_click",
        validate_params=MagicMock(side_effect=lambda payload: payload),
        execute=AsyncMock(return_value='{"ok": false, "status": "not_implemented"}'),
    )
    deps = SimpleNamespace(
        prompt=SimpleNamespace(
            skill_action_execution_service=service,
            action_preflight_message_builder=MagicMock(return_value="preflight summary"),
            action_approval_message_builder=MagicMock(return_value="approval summary"),
            action_execution_message_builder=MagicMock(return_value="execution summary"),
        ),
        build_agent_deps=MagicMock(return_value={}),
        serialize_sse_payload=lambda payload: payload,
        chat_service=MagicMock(),
        tool_registry=SimpleNamespace(get_tools_for_agent=AsyncMock(return_value=[selected_tool])),
    )
    emitter = SimpleNamespace(
        emit=lambda payload: payload,
        event_payload=lambda payload: payload,
    )
    ctx = SimpleNamespace(
        provider="openai",
        model_name="gpt-4o",
        agent_config=SimpleNamespace(),
        tool_event_queue=asyncio.Queue(),
        stream_state=SimpleNamespace(full_response=""),
        chat_id="chat-1",
        assistant_turn_id="turn-1",
        run_id="run-1",
        deps=None,
    )
    request = SimpleNamespace(
        agent_id="agent-1",
        requested_action="click_element",
        requested_action_arguments={"binding_source": "snapshot:browser_snapshot"},
        requested_action_approved=True,
        requested_action_approval_token="approval:browser-operator:1.0.0:click_element:req-browser",
    )
    prompt_prep = SimpleNamespace(
        selected_skill_spec=SimpleNamespace(name="browser-operator", version="1.0.0"),
        final_tools_list=["builtin:browser_click"],
    )
    tool_tracker = SimpleNamespace(on_tool_event=AsyncMock())

    outputs = []
    async for payload in run_requested_action_flow(
        ctx=ctx,
        emitter=emitter,
        tool_tracker=tool_tracker,
        request=request,
        prompt_prep=prompt_prep,
        deps=deps,
    ):
        outputs.append(payload)

    queued_call = transition_calls[0]
    assert queued_call["metadata"]["tool_args"] == {
        "binding_source": "snapshot:browser_snapshot",
        "session_id": "session-1",
        "tab_id": "tab-1",
        "element_ref": "snapshot:browser_snapshot#node:1",
    }
    selected_tool.validate_params.assert_called_once_with(
        {
            "binding_source": "snapshot:browser_snapshot",
            "session_id": "session-1",
            "tab_id": "tab-1",
            "element_ref": "snapshot:browser_snapshot#node:1",
        }
    )
    assert any(isinstance(item, dict) and item.get("lifecycle_status") == "queued" for item in outputs)
    assert any(isinstance(item, dict) and item.get("lifecycle_status") == "running" for item in outputs)
