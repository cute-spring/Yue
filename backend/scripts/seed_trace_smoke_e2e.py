#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed trace smoke E2E data set into YUE_DATA_DIR.")
    parser.add_argument("--data-dir", required=True, help="Target YUE_DATA_DIR path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_root = Path(args.data_dir).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    (target_root / "global_config.json").write_text(
        json.dumps({"feature_flags": {"chat_trace_ui_enabled": False, "chat_trace_raw_enabled": False}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    import os

    os.environ["YUE_DATA_DIR"] = str(target_root)

    from app.core.database import SessionLocal
    from app.models.chat import ActionEvent as ActionEventModel
    from app.models.chat import ActionState as ActionStateModel
    from app.models.chat import Message as MessageModel
    from app.models.chat import Session as SessionModel
    from app.models.chat import SkillEffectivenessEvent as SkillEventModel
    from app.models.chat import ToolCall as ToolCallModel
    from app.services.chat_service import chat_service

    with SessionLocal() as db:
        db.query(ActionEventModel).delete()
        db.query(ActionStateModel).delete()
        db.query(ToolCallModel).delete()
        db.query(SkillEventModel).delete()
        db.query(MessageModel).delete()
        db.query(SessionModel).delete()
        db.commit()

    chat = chat_service.create_chat(title="Trace Smoke Chat")
    assistant_turn_id = "turn-smoke-1"
    run_id = "run-smoke-1"

    chat_service.add_message(chat.id, "user", "Please inspect the last tool chain for this historical run.")
    chat_service.add_message(
        chat.id,
        "assistant",
        "I used docs_search and then summarize_notes to complete the request.",
        assistant_turn_id=assistant_turn_id,
        run_id=run_id,
    )

    snapshot_payload = {
        "event": "chat.request.snapshot",
        "event_id": "evt-snapshot-1",
        "sequence": 1,
        "ts": "2026-04-03T00:50:20Z",
        "snapshot": {
            "chat_id": chat.id,
            "assistant_turn_id": assistant_turn_id,
            "request_id": "req-smoke-1",
            "run_id": run_id,
            "created_at": "2026-04-03T00:50:20Z",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "agent_id": "builtin-action-lab",
            "requested_skill": "trace-smoke-skill",
            "deep_thinking_enabled": False,
            "system_prompt": "You are a precise trace analysis assistant.",
            "user_message": "Please inspect the last tool chain for this historical run.",
            "message_history": [
                {"role": "user", "content_type": "text", "content_summary": "Please inspect the last tool chain for this historical run.", "image_count": 0, "truncated": False}
            ],
            "attachments": [],
            "tool_context": {"selected_tools": ["docs_search", "summarize_notes"]},
            "skill_context": {"active_skill": "trace-smoke-skill"},
            "runtime_flags": {"chat_trace_ui_enabled": True, "chat_trace_raw_enabled": True},
            "redaction": {},
            "truncation": {},
        },
    }
    chat_service.add_action_event(chat.id, snapshot_payload, assistant_turn_id=assistant_turn_id, run_id=run_id)

    trace_1 = {
        "event": "tool.trace.record",
        "event_id": "evt-trace-1",
        "sequence": 2,
        "ts": "2026-04-03T00:50:21Z",
        "trace": {
            "chat_id": chat.id,
            "run_id": run_id,
            "assistant_turn_id": assistant_turn_id,
            "trace_id": "trace-smoke-1",
            "parent_trace_id": None,
            "tool_name": "docs_search",
            "tool_type": "builtin",
            "call_id": "call-smoke-1",
            "call_index": 1,
            "status": "success",
            "started_at": "2026-04-03T00:50:21Z",
            "finished_at": "2026-04-03T00:50:22Z",
            "duration_ms": 147.2,
            "input_arguments": {"query": "tool chain"},
            "output_result": {"hits": 2},
            "error_type": None,
            "error_message": None,
            "error_stack": None,
            "chain_depth": 0,
            "raw_event_id": "evt-trace-1",
        },
    }
    chat_service.add_action_event(chat.id, trace_1, assistant_turn_id=assistant_turn_id, run_id=run_id)

    trace_2 = {
        "event": "tool.trace.record",
        "event_id": "evt-trace-2",
        "sequence": 3,
        "ts": "2026-04-03T00:50:23Z",
        "trace": {
            "chat_id": chat.id,
            "run_id": run_id,
            "assistant_turn_id": assistant_turn_id,
            "trace_id": "trace-smoke-2",
            "parent_trace_id": "trace-smoke-1",
            "tool_name": "summarize_notes",
            "tool_type": "builtin",
            "call_id": "call-smoke-2",
            "call_index": 2,
            "status": "success",
            "started_at": "2026-04-03T00:50:23Z",
            "finished_at": "2026-04-03T00:50:24Z",
            "duration_ms": 123.4,
            "input_arguments": {"max_words": 80},
            "output_result": {"summary": "tool chain summary"},
            "error_type": None,
            "error_message": None,
            "error_stack": None,
            "chain_depth": 1,
            "raw_event_id": "evt-trace-2",
        },
    }
    chat_service.add_action_event(chat.id, trace_2, assistant_turn_id=assistant_turn_id, run_id=run_id)

    print(f"Seeded trace smoke E2E data into: {target_root} (chat_id={chat.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
