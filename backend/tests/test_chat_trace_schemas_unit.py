from datetime import datetime, UTC

from app.api.chat_trace_schemas import (
    ChatTraceBundle,
    RequestAttachmentItem,
    RequestHistoryItem,
    RequestSnapshotRecord,
    ToolTraceRecord,
    build_default_trace_field_policies,
)


def test_request_snapshot_record_round_trip():
    snapshot = RequestSnapshotRecord(
        chat_id="chat-1",
        assistant_turn_id="turn-1",
        request_id="req-1",
        run_id="run-1",
        created_at=datetime(2026, 4, 3, 8, 0, tzinfo=UTC),
        provider="openai",
        model="gpt-4o",
        agent_id="agent-1",
        requested_skill="skill-a",
        deep_thinking_enabled=True,
        system_prompt="system prompt",
        user_message="hello",
        message_history=[
            RequestHistoryItem(role="user", content_type="text", content_summary="hello", truncated=False),
            RequestHistoryItem(role="assistant", content_type="text", content_summary="world", truncated=True),
        ],
        attachments=[
            RequestAttachmentItem(kind="image", name="chart.png", content_type="image/png", size_bytes=128),
        ],
        runtime_flags={"raw_mode": False},
        redaction={"system_prompt": False},
        truncation={"message_history": True},
    )

    restored = RequestSnapshotRecord.model_validate(snapshot.model_dump())

    assert restored.chat_id == "chat-1"
    assert restored.assistant_turn_id == "turn-1"
    assert restored.run_id == "run-1"
    assert restored.message_history[1].truncated is True
    assert restored.attachments[0].name == "chart.png"


def test_tool_trace_record_round_trip_preserves_identifier_fields():
    trace = ToolTraceRecord(
        chat_id="chat-1",
        run_id="run_abc123",
        assistant_turn_id="turn_xyz789",
        trace_id="trace_0001",
        parent_trace_id="trace_root",
        tool_name="docs_search",
        tool_type="builtin",
        call_id="call_123",
        call_index=3,
        status="success",
        started_at=datetime(2026, 4, 3, 8, 0, tzinfo=UTC),
        finished_at=datetime(2026, 4, 3, 8, 0, 1, tzinfo=UTC),
        duration_ms=1000.0,
        input_arguments={"q": "hello"},
        output_result={"ok": True},
        chain_depth=1,
        raw_event_id="evt_123",
    )

    restored = ToolTraceRecord.model_validate(trace.model_dump())

    assert restored.trace_id == "trace_0001"
    assert restored.parent_trace_id == "trace_root"
    assert restored.call_id == "call_123"
    assert restored.status == "success"
    assert restored.input_arguments == {"q": "hello"}


def test_chat_trace_bundle_defaults_to_summary_mode_and_keeps_policies():
    snapshot = RequestSnapshotRecord(
        chat_id="chat-1",
        assistant_turn_id="turn-1",
        request_id="req-1",
        run_id="run-1",
        created_at=datetime(2026, 4, 3, 8, 0, tzinfo=UTC),
        user_message="hello",
    )
    trace = ToolTraceRecord(
        chat_id="chat-1",
        run_id="run-1",
        assistant_turn_id="turn-1",
        trace_id="trace_1",
        tool_name="docs_search",
        status="started",
    )

    bundle = ChatTraceBundle(
        chat_id="chat-1",
        run_id="run-1",
        assistant_turn_id="turn-1",
        snapshot=snapshot,
        tool_traces=[trace],
        field_policies=build_default_trace_field_policies(),
    )

    assert bundle.mode == "summary"
    assert bundle.tool_traces[0].trace_id == "trace_1"
    assert any(policy.field_name == "system_prompt" for policy in bundle.field_policies)


def test_build_default_trace_field_policies_returns_independent_copies():
    policies_a = build_default_trace_field_policies()
    policies_b = build_default_trace_field_policies()

    policies_a[0].reason = "changed"

    assert policies_b[0].reason != "changed"
    assert any(policy.exposure == "raw_only" for policy in policies_b)

