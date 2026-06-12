from types import SimpleNamespace

from app.api.chat_stream_runner_snapshot import (
    build_session_context_event,
    build_workspace_capture_suggestion_event,
    build_workspace_memory_event,
    build_workspace_note_event,
)


def test_build_workspace_note_event_summarizes_note_context_without_prompt_block():
    ctx = SimpleNamespace(
        workspace_note_context={
            "workspace_id": "ws_1",
            "loaded_note_ids": ["note_1"],
            "loaded_notes": [
                {
                    "id": "note_1",
                    "title": "中文输出偏好",
                    "summary": "默认使用中文回复，并保持结构化总结。",
                    "content": "更长的原始内容",
                    "note_type": "preference",
                    "tags": ["中文", "偏好"],
                    "source_session_id": "chat_1",
                    "source_message_id": 42,
                }
            ],
            "prompt_block": "large prompt text should not stream to frontend",
        }
    )

    event = build_workspace_note_event(ctx)

    assert event is not None
    payload = event["workspace_notes"]
    assert payload["workspace_id"] == "ws_1"
    assert payload["loaded_note_ids"] == ["note_1"]
    assert payload["loaded_note_count"] == 1
    assert payload["loaded_notes"][0]["title"] == "中文输出偏好"
    assert "prompt_block" not in payload


def test_build_workspace_capture_suggestion_event_uses_final_response_and_context():
    ctx = SimpleNamespace(
        workspace_note_context={
            "workspace_id": "ws_1",
            "loaded_note_ids": ["note_1"],
            "loaded_notes": [],
        },
        workspace_memory_context={
            "workspace_id": "ws_1",
            "loaded_memory_ids": ["mem_1"],
            "loaded_memories": [],
        },
    )

    event = build_workspace_capture_suggestion_event(
        ctx,
        response_content="总结：默认使用中文回复，并保持结构化结论。这个约定会影响后续所有工作区回答。",
        citations=[{"source_id": "src_1"}],
    )

    assert event is not None
    payload = event["workspace_capture_suggestion"]
    assert payload["workspace_id"] == "ws_1"
    assert payload["show_note_action"] is True
    assert payload["show_memory_action"] is True
    assert payload["citation_count"] == 1
    assert payload["recalled_note_count"] == 1
    assert payload["recalled_memory_count"] == 1
    assert payload["source"] == "backend"


def test_build_session_context_event_summarizes_used_context_sections():
    ctx = SimpleNamespace(
        session_context_used={
            "action": "inject",
            "reason": "Relevant recent context and summary blocks were reused.",
            "recent_event_count": 7,
            "selected_candidate_ids": ["cand_1", "cand_2"],
            "block_names": ["recent_context", "rolling_summary"],
            "sections": [
                {
                    "kind": "recent_context",
                    "label": "Recent context",
                    "summary": "最近两轮关于数据库方案的讨论。",
                    "item_count": 2,
                }
            ],
        }
    )

    event = build_session_context_event(ctx)

    assert event is not None
    payload = event["session_used_context"]
    assert payload["action"] == "inject"
    assert payload["recent_event_count"] == 7
    assert payload["selected_candidate_ids"] == ["cand_1", "cand_2"]
    assert payload["sections"][0]["label"] == "Recent context"


def test_build_workspace_memory_event_includes_scope_type():
    ctx = SimpleNamespace(
        workspace_memory_context={
            "workspace_id": "ws_1",
            "loaded_memory_ids": ["mem_1"],
            "loaded_memories": [
                {
                    "id": "mem_1",
                    "memory_type": "preference",
                    "scope_type": "user",
                    "title": "默认中文输出",
                    "content": "默认中文回复。",
                    "source_session_id": "chat_1",
                    "source_message_id": 42,
                }
            ],
        }
    )

    event = build_workspace_memory_event(ctx)

    assert event is not None
    payload = event["workspace_memory"]
    assert payload["loaded_memory_count"] == 1
    assert payload["loaded_memories"][0]["scope_type"] == "user"
