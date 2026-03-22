import pytest
import json
from unittest.mock import patch

from app.services.contract_gate import (
    classify_sse_event_kind,
    load_contract_schema,
    should_ignore_unknown_event,
    validate_event_payload,
)
from app.api.chat_helpers import serialize_sse_payload


def test_classify_sse_event_kind():
    assert classify_sse_event_kind({"meta": {"provider": "openai"}}) == "meta"
    assert classify_sse_event_kind({"content": "hello"}) == "content"
    assert classify_sse_event_kind({"error": "bad request"}) == "error"
    assert classify_sse_event_kind({"event": "tool.call.started"}) == "tool_event"
    assert classify_sse_event_kind({"event": "skill_effectiveness"}) == "trace_event"


def test_validate_event_payload_by_contract():
    meta_schema = load_contract_schema("sse", "meta")
    content_schema = load_contract_schema("sse", "content")
    tool_schema = load_contract_schema("sse", "tool_event")
    trace_schema = load_contract_schema("sse", "trace_event")

    validate_event_payload(meta_schema, {"meta": {"provider": "openai", "model": "gpt-4o"}})
    validate_event_payload(content_schema, {"content": "你好"})
    validate_event_payload(tool_schema, {"event": "tool.call.started", "call_id": "c1", "tool_name": "docs_search"})
    validate_event_payload(trace_schema, {"event": "skill_effectiveness", "reason_code": "skill_selected"})

    with pytest.raises(ValueError):
        validate_event_payload(content_schema, {"content": 123})


def test_should_ignore_unknown_event():
    assert should_ignore_unknown_event({"event": "future.event.v2"}) is True
    assert should_ignore_unknown_event({"content": "known payload"}) is False


def test_serialize_sse_payload_valid():
    serialized = serialize_sse_payload({"content": "ok"})
    assert serialized.startswith("data: ")
    payload = json.loads(serialized[6:].strip())
    assert payload["content"] == "ok"


def test_serialize_sse_payload_contract_violation_fails_open():
    with patch("app.api.chat_helpers.validate_sse_payload", side_effect=ValueError("bad_contract")):
        serialized = serialize_sse_payload({"meta": {"provider": "openai"}})
    payload = json.loads(serialized[6:].strip())
    assert "stream_contract_violation" in payload["error"]
