import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.services.skill_service import SkillSpec, skill_registry
from app.services.agent_store import AgentConfig
from app.services.chat_service import Message

from datetime import datetime

@pytest.fixture
def client():
    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")

@pytest.fixture
def mock_chat_service():
    with patch("app.api.chat.chat_service") as mock:
        mock.get_session_skill.return_value = (None, None)
        yield mock

def test_list_chats(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.list_chats.return_value = [
        {"id": "1", "title": "Chat 1", "created_at": now, "updated_at": now, "messages": []}
    ]
    response = client.get("/api/chat/history")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "1"

def test_get_chat_success(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.get_chat.return_value = {
        "id": "1", "title": "Chat 1", "created_at": now, "updated_at": now, "messages": []
    }
    response = client.get("/api/chat/1")
    assert response.status_code == 200
    assert response.json()["id"] == "1"

def test_get_chat_not_found(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = None
    response = client.get("/api/chat/non_existent")
    assert response.status_code == 404

def test_delete_chat_success(client, mock_chat_service):
    mock_chat_service.delete_chat.return_value = True
    response = client.delete("/api/chat/1")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_delete_chat_not_found(client, mock_chat_service):
    mock_chat_service.delete_chat.return_value = False
    response = client.delete("/api/chat/non_existent")
    assert response.status_code == 404

def test_get_skill_effectiveness_report_endpoint(client, mock_chat_service):
    mock_chat_service.get_skill_effectiveness_report.return_value = {
        "window_hours": 24,
        "total_runs": 10,
        "skill_hit_rate": 0.8,
        "fallback_rate": 0.2,
        "avg_system_prompt_tokens": 120.0,
        "avg_user_message_tokens": 22.0,
        "reason_distribution": [{"reason_code": "skill_selected", "count": 8}],
        "top_selected_skills": [{"name": "pdf-insight-extractor", "count": 5}],
    }
    response = client.get("/api/chat/skill-effectiveness/report?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 10
    assert "reason_distribution" in data
    bad = client.get("/api/chat/skill-effectiveness/report?hours=0")
    assert bad.status_code == 400

def test_truncate_chat(client, mock_chat_service):
    response = client.post("/api/chat/1/truncate", json={"keep_count": 5})
    assert response.status_code == 200
    mock_chat_service.truncate_chat.assert_called_once_with("1", 5)

def test_generate_summary_not_found(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = None
    response = client.post("/api/chat/missing/summary")
    assert response.status_code == 404

def test_generate_summary_updates_session(client, mock_chat_service):
    now = datetime.now()
    class DummyChat:
        def __init__(self, summary):
            self.id = "1"
            self.title = "Chat 1"
            self.summary = summary
            self.created_at = now
            self.updated_at = now
            self.messages = []
            self.active_skill_name = None
            self.active_skill_version = None
    mock_chat_service.get_chat.side_effect = [
        DummyChat(None),
        DummyChat("new summary")
    ]
    with patch("app.api.chat.session_meta_service.generate_session_meta", new=AsyncMock(return_value="new summary")):
        response = client.post("/api/chat/1/summary")
    assert response.status_code == 200
    assert response.json()["summary"] == "new summary"
    mock_chat_service.update_chat_summary.assert_called_once_with("1", "new summary")

def test_get_chat_meta_not_found(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = None
    response = client.get("/api/chat/missing/meta")
    assert response.status_code == 404

def test_get_chat_meta_success(client, mock_chat_service):
    now = datetime.now()
    chat_obj = MagicMock()
    chat_obj.id = "1"
    chat_obj.title = "Refined Title"
    chat_obj.summary = "Summary"
    chat_obj.updated_at = now
    mock_chat_service.get_chat.return_value = chat_obj
    response = client.get("/api/chat/1/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "1"
    assert payload["title"] == "Refined Title"
    assert payload["summary"] == "Summary"


def test_get_chat_trace_bundle_success(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_chat_trace_bundle.return_value = {
        "mode": "summary",
        "chat_id": "1",
        "run_id": "run-1",
        "assistant_turn_id": "turn-1",
        "snapshot": {
            "chat_id": "1",
            "assistant_turn_id": "turn-1",
            "request_id": "req-1",
            "run_id": "run-1",
            "created_at": datetime.now().isoformat(),
            "system_prompt": None,
            "user_message": "hello",
            "message_history": [],
            "attachments": [],
            "tool_context": {},
            "skill_context": {},
            "runtime_flags": {},
            "redaction": {"system_prompt": True},
            "truncation": {},
        },
        "tool_traces": [],
        "field_policies": [],
    }

    response = client.get("/api/chat/1/trace/bundle")

    assert response.status_code == 200
    assert response.json()["mode"] == "summary"
    mock_chat_service.get_chat_trace_bundle.assert_called_once_with("1", assistant_turn_id=None, mode="summary")


def test_get_chat_trace_bundle_not_found(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_chat_trace_bundle.return_value = None

    response = client.get("/api/chat/1/trace/bundle")

    assert response.status_code == 404


def test_get_chat_trace_bundle_rejects_unsupported_mode(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_chat_trace_bundle.side_effect = ValueError("Unsupported trace bundle mode")

    response = client.get("/api/chat/1/trace/bundle?mode=raw")

    assert response.status_code == 403
    assert "Raw trace mode is disabled" in response.json()["detail"]


def test_get_chat_trace_bundle_raw_mode_success_when_enabled(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_chat_trace_bundle.return_value = {
        "mode": "raw",
        "chat_id": "1",
        "run_id": "run-1",
        "assistant_turn_id": "turn-1",
        "snapshot": {
            "chat_id": "1",
            "assistant_turn_id": "turn-1",
            "request_id": "req-1",
            "run_id": "run-1",
            "created_at": datetime.now().isoformat(),
            "system_prompt": "raw prompt",
            "user_message": "hello",
            "message_history": [],
            "attachments": [],
            "tool_context": {},
            "skill_context": {},
            "runtime_flags": {},
            "redaction": {},
            "truncation": {},
        },
        "tool_traces": [],
        "field_policies": [],
    }

    with patch("app.api.chat.config_service.get_feature_flags", return_value={"chat_trace_raw_enabled": True}):
        response = client.get("/api/chat/1/trace/bundle?mode=raw")

    assert response.status_code == 200
    assert response.json()["mode"] == "raw"
    mock_chat_service.get_chat_trace_bundle.assert_called_once_with("1", assistant_turn_id=None, mode="raw")


def test_get_chat_trace_bundle_invalid_mode_returns_400_when_raw_gate_passes(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_chat_trace_bundle.side_effect = ValueError("Unsupported trace bundle mode")

    with patch("app.api.chat.config_service.get_feature_flags", return_value={"chat_trace_raw_enabled": True}):
        response = client.get("/api/chat/1/trace/bundle?mode=invalid")

    assert response.status_code == 400
    assert "Unsupported trace bundle mode" in response.json()["detail"]

def test_get_action_state_by_skill_and_action(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_action_state.return_value = {
        "id": 1,
        "session_id": "1",
        "skill_name": "action-skill",
        "skill_version": "1.0.0",
        "action_id": "generate",
        "invocation_id": "invoke:action-skill:1.0.0:generate:req-approval",
        "approval_token": "approval:action-skill:1.0.0:generate:req-approval",
        "request_id": "req-approval",
        "run_id": "run-1",
        "assistant_turn_id": "turn-1",
        "lifecycle_phase": "execution",
        "lifecycle_status": "awaiting_approval",
        "status": "awaiting_approval",
        "payload": {"event": "skill.action.result"},
        "created_at": now,
        "updated_at": now,
    }

    response = client.get("/api/chat/1/actions/state?skill_name=action-skill&action_id=generate")

    assert response.status_code == 200
    assert response.json()["action_id"] == "generate"
    mock_chat_service.get_action_state.assert_called_once_with(
        "1",
        skill_name="action-skill",
        action_id="generate",
    )

def test_get_action_state_by_approval_token(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_action_state_by_approval_token.return_value = {
        "id": 1,
        "session_id": "1",
        "skill_name": "action-skill",
        "skill_version": "1.0.0",
        "action_id": "generate",
        "invocation_id": "invoke:action-skill:1.0.0:generate:req-approval",
        "approval_token": "approval:action-skill:1.0.0:generate:req-approval",
        "request_id": "req-approval",
        "run_id": "run-1",
        "assistant_turn_id": "turn-1",
        "lifecycle_phase": "execution",
        "lifecycle_status": "awaiting_approval",
        "status": "awaiting_approval",
        "payload": {"event": "skill.action.result"},
        "created_at": now,
        "updated_at": now,
    }

    response = client.get("/api/chat/1/actions/state?approval_token=approval:action-skill:1.0.0:generate:req-approval")

    assert response.status_code == 200
    assert response.json()["approval_token"] == "approval:action-skill:1.0.0:generate:req-approval"
    mock_chat_service.get_action_state_by_approval_token.assert_called_once_with(
        "1",
        approval_token="approval:action-skill:1.0.0:generate:req-approval",
    )

def test_get_action_state_by_invocation_id(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.get_action_state_by_invocation_id.return_value = {
        "id": 1,
        "session_id": "1",
        "skill_name": "action-skill",
        "skill_version": "1.0.0",
        "action_id": "generate",
        "invocation_id": "invoke:action-skill:1.0.0:generate:req-approval",
        "approval_token": "approval:action-skill:1.0.0:generate:req-approval",
        "request_id": "req-approval",
        "run_id": "run-1",
        "assistant_turn_id": "turn-1",
        "lifecycle_phase": "execution",
        "lifecycle_status": "awaiting_approval",
        "status": "awaiting_approval",
        "payload": {"event": "skill.action.result"},
        "created_at": now,
        "updated_at": now,
    }

    response = client.get("/api/chat/1/actions/state?invocation_id=invoke:action-skill:1.0.0:generate:req-approval")

    assert response.status_code == 200
    assert response.json()["invocation_id"] == "invoke:action-skill:1.0.0:generate:req-approval"
    mock_chat_service.get_action_state_by_invocation_id.assert_called_once_with(
        "1",
        invocation_id="invoke:action-skill:1.0.0:generate:req-approval",
    )

def test_get_action_state_rejects_mixed_lookup_modes(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")

    response = client.get(
        "/api/chat/1/actions/state?skill_name=action-skill&action_id=generate&approval_token=approval:token"
    )

    assert response.status_code == 400
    assert "Use exactly one lookup mode" in response.json()["detail"]

def test_get_action_state_rejects_incomplete_lookup(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = MagicMock(id="1")

    response = client.get("/api/chat/1/actions/state?skill_name=action-skill")

    assert response.status_code == 400
    assert "required together" in response.json()["detail"]

def test_list_action_states(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.get_chat.return_value = MagicMock(id="1")
    mock_chat_service.list_action_states.return_value = [
        {
            "id": 1,
            "session_id": "1",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "invocation_id": "invoke:action-skill:1.0.0:generate:req-approval",
            "approval_token": "approval:action-skill:1.0.0:generate:req-approval",
            "request_id": "req-approval",
            "run_id": "run-1",
            "assistant_turn_id": "turn-1",
            "lifecycle_phase": "execution",
            "lifecycle_status": "awaiting_approval",
            "status": "awaiting_approval",
            "payload": {"event": "skill.action.result"},
            "created_at": now,
            "updated_at": now,
        }
    ]

    response = client.get("/api/chat/1/actions/states")

    assert response.status_code == 200
    assert response.json()[0]["skill_name"] == "action-skill"
    mock_chat_service.list_action_states.assert_called_once_with("1")

@pytest.mark.asyncio
async def test_chat_stream_basic(client, mock_chat_service):
    # This is a complex test because of StreamingResponse and many dependencies
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model") as mock_get_model, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Mock run_stream context manager
        mock_result = MagicMock()
        
        # Mocking an async generator for stream_text
        async def mock_stream():
            yield "Hello"
            yield "Hello world"

        # stream_text should be a normal method returning an async iterable
        mock_result.stream_text.return_value = mock_stream()
        
        # mock_agent.run_stream is an async context manager
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        
        # Collect streaming output
        # TestClient with StreamingResponse returns strings in iter_lines if it detects text
        lines = [line for line in response.iter_lines()]
        data_lines = [line for line in lines if line.startswith("data: ")]
        
        assert len(data_lines) >= 3 # chat_id, meta, content
        assert "new-chat-id" in data_lines[0]
        assert any('"event": "skill_effectiveness"' in line for line in data_lines)
        assert any('"meta"' in line for line in data_lines)
        assert any("Hello" in line for line in data_lines)
        assert any(" world" in line for line in data_lines)


@pytest.mark.asyncio
async def test_chat_stream_validates_sse_contract(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat_helpers.validate_sse_payload") as mock_validate:
        mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        mock_result = MagicMock()

        async def mock_stream():
            yield "Hello"
            yield "Hello world"

        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200

        payloads = [call.args[0] for call in mock_validate.call_args_list if call.args]
        assert any(isinstance(item, dict) and "meta" in item for item in payloads)
        assert any(isinstance(item, dict) and "content" in item for item in payloads)


@pytest.mark.asyncio
async def test_chat_stream_contract_violation_fails_open(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat_helpers.validate_sse_payload") as mock_validate:
        mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        mock_result = MagicMock()

        async def mock_stream():
            yield "Hello"

        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        def side_effect(payload):
            if isinstance(payload, dict) and "meta" in payload:
                raise ValueError("broken_meta_contract")
            return None

        mock_validate.side_effect = side_effect
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        found_contract_violation = False
        found_hello = False
        for line in response.iter_lines():
            if "stream_contract_violation" in line:
                found_contract_violation = True
            if "Hello" in line:
                found_hello = True
            if found_contract_violation and found_hello:
                break
        assert found_contract_violation
        assert found_hello


@pytest.mark.asyncio
async def test_chat_stream_requested_action_emits_preflight_events_and_skips_model_run(client, mock_chat_service):
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:exec"]
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:exec
    resource: generate
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.tool_registry") as mock_registry, \
                 patch("app.api.chat.get_model") as mock_get_model, \
                 patch("app.api.chat.Agent") as mock_agent_cls:
                mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
                mock_registry.get_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_store.get_agent.return_value = AgentConfig(
                    id="action-agent",
                    name="Action Agent",
                    system_prompt="You are an action agent.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:exec"],
                    skill_mode="manual",
                    visible_skills=[],
                    resolved_visible_skills=["action-skill:1.0.0"],
                )

                response = client.post(
                    "/api/chat/stream",
                    json={
                        "message": "Run action preflight",
                        "agent_id": "action-agent",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "requested_skill": "action-skill:1.0.0",
                        "requested_action": "generate",
                    },
                )
                assert response.status_code == 200

                lines = [line for line in response.iter_lines()]
                data_lines = [line for line in lines if line.startswith("data: ")]
                assert any('"event": "skill.action.preflight"' in line for line in data_lines)
                assert any('"event": "skill.action.result"' in line for line in data_lines)
                assert any('"lifecycle_status": "preflight_approval_required"' in line for line in data_lines)
                assert any('"lifecycle_status": "awaiting_approval"' in line for line in data_lines)
                assert any('"mapped_tool": "builtin:exec"' in line for line in data_lines)
                assert any("requires approval before any platform-tool continuation" in line for line in data_lines)
                assert any("is awaiting approval before any platform-tool continuation can be considered" in line for line in data_lines)
                assert mock_chat_service.add_action_event.call_count == 3
                mock_registry.get_pydantic_ai_tools_for_agent.assert_not_called()
                mock_get_model.assert_not_called()
                mock_agent_cls.assert_not_called()
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()


@pytest.mark.asyncio
async def test_chat_stream_requested_action_resume_after_approval_emits_approval_and_execution_events(client, mock_chat_service):
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:exec"]
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:exec
    resource: generate
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.tool_registry") as mock_registry, \
                 patch("app.api.chat.get_model") as mock_get_model, \
                 patch("app.api.chat.Agent") as mock_agent_cls:
                mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
                mock_exec_tool = MagicMock()
                mock_exec_tool.name = "exec"
                mock_exec_tool.validate_params.side_effect = lambda args: args
                mock_exec_tool.execute = AsyncMock(return_value="pwd\n/Users/gavinzhang/ws-ai-recharge-2026/Yue")
                mock_registry.get_tools_for_agent = AsyncMock(return_value=[mock_exec_tool])

                mock_agent_store.get_agent.return_value = AgentConfig(
                    id="action-agent",
                    name="Action Agent",
                    system_prompt="You are an action agent.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:exec"],
                    skill_mode="manual",
                    visible_skills=[],
                    resolved_visible_skills=["action-skill:1.0.0"],
                )

                response = client.post(
                    "/api/chat/stream",
                    json={
                        "message": "Approve and continue",
                        "agent_id": "action-agent",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "requested_skill": "action-skill:1.0.0",
                        "requested_action": "generate",
                        "requested_action_arguments": {"command": "pwd", "cwd": "/Users/gavinzhang/ws-ai-recharge-2026/Yue"},
                        "requested_action_approved": True,
                        "requested_action_approval_token": "approval:action-skill:1.0.0:generate:manual",
                    },
                )
                assert response.status_code == 200

                lines = [line for line in response.iter_lines()]
                data_lines = [line for line in lines if line.startswith("data: ")]
                assert any('"event": "skill.action.approval"' in line for line in data_lines)
                assert any('"lifecycle_status": "approved"' in line for line in data_lines)
                assert any('"lifecycle_status": "queued"' in line for line in data_lines)
                assert any('"lifecycle_status": "running"' in line for line in data_lines)
                assert any('"lifecycle_status": "succeeded"' in line for line in data_lines)
                assert any('"event": "tool.call.started"' in line for line in data_lines)
                assert any('"event": "tool.call.finished"' in line for line in data_lines)
                assert any('"mapped_tool": "builtin:exec"' in line for line in data_lines)
                assert any('"tool_args": {"command": "pwd", "cwd": "/Users/gavinzhang/ws-ai-recharge-2026/Yue"}' in line for line in data_lines)
                assert any("was approved. Platform-tool action flow can continue" in line for line in data_lines)
                assert any("[Tool Result] `builtin:exec` returned:" in line for line in data_lines)
                assert mock_chat_service.add_action_event.call_count == 6
                mock_chat_service.add_tool_call.assert_called_once()
                mock_chat_service.update_tool_call.assert_called_once()
                mock_registry.get_pydantic_ai_tools_for_agent.assert_not_called()
                mock_get_model.assert_not_called()
                mock_agent_cls.assert_not_called()
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_chat_stream_requested_action_blocks_on_invalid_action_arguments(client, mock_chat_service):
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:exec"]
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:exec
    resource: generate
    input_schema:
      type: object
      properties:
        command:
          type: string
      required: ["command"]
      additionalProperties: false
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.tool_registry") as mock_registry, \
                 patch("app.api.chat.get_model") as mock_get_model, \
                 patch("app.api.chat.Agent") as mock_agent_cls:
                mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
                mock_registry.get_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_store.get_agent.return_value = AgentConfig(
                    id="action-agent",
                    name="Action Agent",
                    system_prompt="You are an action agent.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:exec"],
                    skill_mode="manual",
                    visible_skills=[],
                    resolved_visible_skills=["action-skill:1.0.0"],
                )

                response = client.post(
                    "/api/chat/stream",
                    json={
                        "message": "Run action preflight",
                        "agent_id": "action-agent",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "requested_skill": "action-skill:1.0.0",
                        "requested_action": "generate",
                        "requested_action_arguments": {"working_dir": "."},
                    },
                )
                assert response.status_code == 200

                lines = [line for line in response.iter_lines()]
                data_lines = [line for line in lines if line.startswith("data: ")]
                assert any('"lifecycle_status": "preflight_blocked"' in line for line in data_lines)
                assert any("Missing required action argument: command" in line for line in data_lines)
                mock_registry.get_tools_for_agent.assert_not_called()
                mock_get_model.assert_not_called()
                mock_agent_cls.assert_not_called()
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_chat_stream_requested_action_surfaces_nested_argument_validation_paths(client, mock_chat_service):
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:exec"]
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:exec
    resource: generate
    input_schema:
      type: object
      properties:
        options:
          type: object
          properties:
            cwd:
              type: string
          required: ["cwd"]
          additionalProperties: false
        targets:
          type: array
          items:
            type: object
            properties:
              path:
                type: string
              mode:
                type: string
                enum: ["read", "write"]
            required: ["path", "mode"]
            additionalProperties: false
      required: ["options"]
      additionalProperties: false
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.tool_registry") as mock_registry, \
                 patch("app.api.chat.get_model") as mock_get_model, \
                 patch("app.api.chat.Agent") as mock_agent_cls:
                mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
                mock_registry.get_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_store.get_agent.return_value = AgentConfig(
                    id="action-agent",
                    name="Action Agent",
                    system_prompt="You are an action agent.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:exec"],
                    skill_mode="manual",
                    visible_skills=[],
                    resolved_visible_skills=["action-skill:1.0.0"],
                )

                response = client.post(
                    "/api/chat/stream",
                    json={
                        "message": "Run action preflight",
                        "agent_id": "action-agent",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "requested_skill": "action-skill:1.0.0",
                        "requested_action": "generate",
                        "requested_action_arguments": {
                            "options": {"extra": True},
                            "targets": [{"path": "docs", "mode": "delete"}],
                        },
                    },
                )
                assert response.status_code == 200

                lines = [line for line in response.iter_lines()]
                data_lines = [line for line in lines if line.startswith("data: ")]
                assert any('"lifecycle_status": "preflight_blocked"' in line for line in data_lines)
                assert any("Missing required action argument: options.cwd" in line for line in data_lines)
                assert any("Unexpected action argument: options.extra" in line for line in data_lines)
                assert any("Invalid value for action argument `targets[0].mode`" in line for line in data_lines)
                mock_registry.get_tools_for_agent.assert_not_called()
                mock_get_model.assert_not_called()
                mock_agent_cls.assert_not_called()
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_chat_stream_requested_action_blocks_on_nested_schema_constraints(client, mock_chat_service):
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:exec"]
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:exec
    resource: generate
    input_schema:
      type: object
      properties:
        options:
          type: object
          properties:
            cwd:
              type: string
              minLength: 4
              pattern: "^/"
          required: ["cwd"]
          additionalProperties: false
        retries:
          type: integer
          minimum: 1
          maximum: 3
      required: ["options", "retries"]
      additionalProperties: false
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.tool_registry") as mock_registry, \
                 patch("app.api.chat.get_model") as mock_get_model, \
                 patch("app.api.chat.Agent") as mock_agent_cls:
                mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
                mock_registry.get_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_store.get_agent.return_value = AgentConfig(
                    id="action-agent",
                    name="Action Agent",
                    system_prompt="You are an action agent.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:exec"],
                    skill_mode="manual",
                    visible_skills=[],
                    resolved_visible_skills=["action-skill:1.0.0"],
                )

                response = client.post(
                    "/api/chat/stream",
                    json={
                        "message": "Run action preflight",
                        "agent_id": "action-agent",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "requested_skill": "action-skill:1.0.0",
                        "requested_action": "generate",
                        "requested_action_arguments": {
                            "options": {"cwd": "tmp"},
                            "retries": 0,
                        },
                    },
                )
                assert response.status_code == 200

                lines = [line for line in response.iter_lines()]
                data_lines = [line for line in lines if line.startswith("data: ")]
                assert any('"lifecycle_status": "preflight_blocked"' in line for line in data_lines)
                assert any("String action argument `options.cwd` must have length >= 4" in line for line in data_lines)
                assert any("String action argument `options.cwd` must match pattern `^/`" in line for line in data_lines)
                assert any("Numeric action argument `retries` must be >= 1" in line for line in data_lines)
                mock_registry.get_tools_for_agent.assert_not_called()
                mock_get_model.assert_not_called()
                mock_agent_cls.assert_not_called()
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

def test_estimate_tokens():
    from app.api.chat import estimate_tokens
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcdef") == 2

def test_build_history_from_chat_preserves_order_and_images():
    from app.api import chat as chat_api

    chat_obj = MagicMock()
    chat_obj.messages = [
        Message(role="user", content="first", timestamp=datetime.now()),
        Message(role="assistant", content="reply", timestamp=datetime.now()),
        Message(role="user", content="with image", images=["/tmp/example.png"], timestamp=datetime.now()),
    ]

    with patch("app.api.chat.load_image_to_base64", return_value="base64data"):
        history = chat_api._build_history_from_chat(chat_obj)

    assert len(history) == 3
    assert history[0].parts[0].content == "first"
    assert history[1].parts[0].content == "reply"
    last_parts = history[2].parts[0].content
    assert last_parts[0] == "with image"
    assert getattr(last_parts[1], "url", None) == "base64data"

def test_resolve_skill_runtime_state_manual_explicit_selection(mock_chat_service):
    from app.api import chat as chat_api

    fake_agent = AgentConfig(
        id="skill-agent",
        name="Skill Agent",
        system_prompt="persona",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read"],
        skill_mode="manual",
        visible_skills=["pdf-insight-extractor:1.0.0"],
    )
    fake_skill = SkillSpec(
        name="pdf-insight-extractor",
        version="1.0.0",
        description="pdf",
        capabilities=["pdf-analysis"],
        entrypoint="system_prompt",
        system_prompt="YOU ARE A PDF SKILL.",
    )

    with patch("app.api.chat.skill_router.resolve_visible_skill_refs", return_value=["pdf-insight-extractor:1.0.0"]), \
         patch("app.api.chat.skill_router.get_visible_skills", return_value=[fake_skill]), \
         patch("app.api.chat.skill_router.infer_requested_skill", return_value=None), \
         patch("app.api.chat.skill_router.route_with_score", return_value=(fake_skill, 8)):
        state = chat_api._resolve_skill_runtime_state(
            agent_config=fake_agent,
            feature_flags={"skill_runtime_enabled": True, "skill_summary_prompt_enabled": True},
            chat_id="chat-id",
            request_message="please analyze this pdf",
            requested_skill="pdf-insight-extractor:1.0.0",
        )

    assert state["selected_skill_spec"] == fake_skill
    assert state["selection_reason_code"] == "skill_selected"
    assert state["selection_source"] == "explicit"
    assert state["visible_skill_count"] == 1
    assert state["available_skill_count"] == 1
    assert "### Skill Summaries" in state["summary_block"]
    mock_chat_service.set_session_skill.assert_called_once_with("chat-id", "pdf-insight-extractor", "1.0.0")

@pytest.mark.asyncio
async def test_chat_stream_ollama_502(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.fetch_ollama_models") as mock_fetch, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_fetch.return_value = ["gpt-4o"]
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None
        
        # Ensure tools are mockable/serializable
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Simulate exception during run_stream
        # We need to mock the async context manager correctly
        mock_agent.run_stream.side_effect = Exception("status_code: 502")
        
        response = client.post("/api/chat/stream", json={"message": "hi", "provider": "ollama"})
        assert response.status_code == 200
        found_ollama = False
        found_502 = False
        for line in response.iter_lines():
            if "Ollama" in line:
                found_ollama = True
            if "502" in line:
                found_502 = True
            if found_ollama and found_502:
                break
        assert found_ollama and found_502

@pytest.mark.asyncio
async def test_chat_stream_no_tools_fallback(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model") as mock_get_model, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None
        
        # Mock tool with a name attribute
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[mock_tool])
        
        # First agent (with tools) fails with "does not support tools"
        mock_agent_with_tools = MagicMock()
        mock_agent_with_tools.run_stream.side_effect = Exception("does not support tools")
        
        # Second agent (without tools) succeeds
        mock_agent_no_tools = MagicMock()
        mock_agent_cls.side_effect = [mock_agent_with_tools, mock_agent_no_tools]
        
        mock_result = MagicMock()
        async def mock_stream():
            yield "Fallback response"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent_no_tools.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent_no_tools.run_stream.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        lines = [line for line in response.iter_lines()]
        assert any("Fallback response" in line for line in lines)

@pytest.mark.asyncio
async def test_chat_stream_emits_skill_effectiveness_event(client, mock_chat_service):
    with patch.dict("os.environ", {"PROMPT_SCOPE_SUMMARY_ENABLED": "true"}, clear=False), \
         patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.config_service.get_feature_flags", return_value={
             "skill_runtime_enabled": True,
             "skill_selector_tool_enabled": True,
             "skill_auto_mode_enabled": True,
             "skill_summary_prompt_enabled": True,
             "skill_lazy_full_load_enabled": True,
         }), \
         patch("app.api.chat.skill_router.get_visible_skills") as mock_visible, \
         patch("app.api.chat.skill_router.route_with_score") as mock_route_with_score, \
         patch("app.api.chat.skill_registry.get_full_skill") as mock_get_full:
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

        fake_agent = AgentConfig(
            id="skill-agent",
            name="Skill Agent",
            system_prompt="YOU ARE A LEGACY AGENT.",
            provider="openai",
            model="gpt-4o",
            enabled_tools=["builtin:docs_read"],
            skill_mode="auto",
            visible_skills=["pdf-insight-extractor:1.0.0"]
        )
        fake_skill = SkillSpec(
            name="pdf-insight-extractor",
            version="1.0.0",
            description="pdf",
            capabilities=["pdf-analysis"],
            entrypoint="system_prompt",
            system_prompt="YOU ARE A PDF SKILL."
        )
        mock_agent_store.get_agent.return_value = fake_agent
        mock_visible.return_value = [fake_skill]
        mock_route_with_score.return_value = (fake_skill, 8)
        mock_get_full.return_value = fake_skill

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream():
            yield "done"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "请分析这个 PDF", "agent_id": "skill-agent"})
        assert response.status_code == 200
        data_lines = [line[6:] for line in response.iter_lines() if line.startswith("data: ")]
        payloads = []
        for raw in data_lines:
            try:
                payloads.append(json.loads(raw))
            except Exception:
                pass
        effects = [p for p in payloads if p.get("event") == "skill_effectiveness"]
        assert effects
        effect = effects[0]
        assert effect["reason_code"] == "skill_selected"
        assert effect["fallback_used"] is False
        assert effect["selected_skill"]["name"] == "pdf-insight-extractor"
        assert effect["scope_summary_injected"] is True
        assert effect["effective_scope_count"] > 0
        assert effect["system_prompt_tokens_estimate"] > 0

@pytest.mark.asyncio
async def test_chat_stream_with_images(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.save_base64_image") as mock_save, \
         patch("app.api.chat.load_image_to_base64") as mock_load, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_save.return_value = "/path/to/img.png"
        mock_load.return_value = "base64data"
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        
        # Mock history with images
        from app.services.chat_service import Message
        mock_chat = MagicMock()
        mock_chat.messages = [Message(role="user", content="hi", images=["/old/img.png"], timestamp=datetime.now())]
        mock_chat_service.get_chat.return_value = mock_chat
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream(): yield "Hi"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        
        response = client.post("/api/chat/stream", json={
            "message": "look at this",
            "images": ["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="],
            "chat_id": "chat-id"
        })
        assert response.status_code == 200
        mock_save.assert_called_once()
        mock_load.assert_called_once()

@pytest.mark.asyncio
async def test_refine_title_once_updates_only_placeholder_title():
    from app.api import chat as chat_api
    user_text = "A" * 35
    placeholder_title = "A" * 30 + "..."
    chat_obj = MagicMock()
    chat_obj.title = placeholder_title
    chat_obj.messages = [
        Message(role="user", content=user_text, timestamp=datetime.now()),
        Message(role="assistant", content="assistant answer", timestamp=datetime.now()),
    ]
    with patch("app.api.chat.chat_service") as mock_service, \
         patch("app.api.chat.session_meta_service") as mock_meta:
        mock_service.get_chat.return_value = chat_obj
        mock_meta.generate_session_meta = AsyncMock(return_value="Refined Title")
        await chat_api._refine_title_once("chat-id")
        mock_meta.generate_session_meta.assert_called_once()
        _, kwargs = mock_meta.generate_session_meta.call_args
        assert kwargs.get("task") == "title"
        mock_service.update_chat_title.assert_called_once_with("chat-id", "Refined Title")

@pytest.mark.asyncio
async def test_refine_title_once_skips_manual_title():
    from app.api import chat as chat_api
    chat_obj = MagicMock()
    chat_obj.title = "Manual Name"
    chat_obj.messages = [
        Message(role="user", content="hello", timestamp=datetime.now()),
        Message(role="assistant", content="assistant answer", timestamp=datetime.now()),
    ]
    with patch("app.api.chat.chat_service") as mock_service, \
         patch("app.api.chat.session_meta_service") as mock_meta:
        mock_service.get_chat.return_value = chat_obj
        mock_meta.generate_session_meta = AsyncMock(return_value="Refined Title")
        await chat_api._refine_title_once("chat-id")
        mock_meta.generate_session_meta.assert_not_called()
        mock_service.update_chat_title.assert_not_called()

@pytest.mark.asyncio
async def test_refine_title_once_forwards_runtime_provider_model():
    from app.api import chat as chat_api
    chat_obj = MagicMock()
    chat_obj.title = "A" * 30 + "..."
    chat_obj.messages = [
        Message(role="user", content="A" * 35, timestamp=datetime.now()),
        Message(role="assistant", content="assistant answer", timestamp=datetime.now()),
    ]
    with patch("app.api.chat.chat_service") as mock_service, \
         patch("app.api.chat.session_meta_service") as mock_meta, \
         patch("app.api.chat.config_service.get_llm_config", return_value={"meta_use_runtime_model_for_title": True}):
        mock_service.get_chat.return_value = chat_obj
        mock_meta.generate_session_meta = AsyncMock(return_value="Refined Title")
        await chat_api._refine_title_once("chat-id", provider_override="zhipu", model_override="glm-4.6v")
        mock_meta.generate_session_meta.assert_called_once()
        _, kwargs = mock_meta.generate_session_meta.call_args
        assert kwargs.get("provider_override") == "zhipu"
        assert kwargs.get("model_override") == "glm-4.6v"

@pytest.mark.asyncio
async def test_refine_title_once_ignores_runtime_provider_model_when_disabled():
    from app.api import chat as chat_api
    chat_obj = MagicMock()
    chat_obj.title = "A" * 30 + "..."
    chat_obj.messages = [
        Message(role="user", content="A" * 35, timestamp=datetime.now()),
        Message(role="assistant", content="assistant answer", timestamp=datetime.now()),
    ]
    with patch("app.api.chat.chat_service") as mock_service, \
         patch("app.api.chat.session_meta_service") as mock_meta, \
         patch("app.api.chat.config_service.get_llm_config", return_value={"meta_use_runtime_model_for_title": False}):
        mock_service.get_chat.return_value = chat_obj
        mock_meta.generate_session_meta = AsyncMock(return_value="Refined Title")
        await chat_api._refine_title_once("chat-id", provider_override="zhipu", model_override="glm-4.6v")
        mock_meta.generate_session_meta.assert_called_once()
        _, kwargs = mock_meta.generate_session_meta.call_args
        assert kwargs.get("provider_override") is None
        assert kwargs.get("model_override") is None

def test_title_refinement_reason_distribution_endpoint(client, mock_chat_service):
    from app.api import chat as chat_api
    chat_api._TITLE_REFINEMENT_REASON_COUNTS.clear()
    chat_api._TITLE_REFINEMENT_REASON_COUNTS["updated"] = 2
    chat_api._TITLE_REFINEMENT_REASON_COUNTS["non_placeholder"] = 3
    response = client.get("/api/chat/title-refinement/reasons")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert payload["counts"]["updated"] == 2
    assert payload["counts"]["non_placeholder"] == 3

def test_record_title_refinement_reason_counts():
    from app.api import chat as chat_api
    chat_api._TITLE_REFINEMENT_REASON_COUNTS.clear()
    chat_api._record_title_refinement_reason("updated")
    chat_api._record_title_refinement_reason("updated")
    chat_api._record_title_refinement_reason("non_placeholder")
    distribution = chat_api._title_refinement_reason_distribution()
    assert distribution["total"] == 3
    assert distribution["counts"]["updated"] == 2
    assert distribution["counts"]["non_placeholder"] == 1

@pytest.mark.asyncio
async def test_chat_stream_with_agent_config(client, mock_chat_service):
    with patch.dict("os.environ", {"PROMPT_SCOPE_SUMMARY_ENABLED": "true"}, clear=False), \
         patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_agent_config = MagicMock()
        mock_agent_config.provider = "anthropic"
        mock_agent_config.model = "claude-3-opus"
        mock_agent_config.system_prompt = "You are a scientist."
        mock_agent_config.doc_roots = ["/docs"]
        mock_agent_config.enabled_tools = ["builtin:docs_read"]
        mock_agent_store.get_agent.return_value = mock_agent_config
        
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream(): yield "Result"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        
        response = client.post("/api/chat/stream", json={"message": "hi", "agent_id": "sci-agent"})
        assert response.status_code == 200
        # Check if agent was created with merged config
        assert mock_agent_cls.called
        args, kwargs = mock_agent_cls.call_args
        assert "scientist" in kwargs["system_prompt"]
        assert "可检索目录" in kwargs["system_prompt"]
        assert "### Scope Summary" in kwargs["system_prompt"]
        assert "docs" in kwargs["system_prompt"]

@pytest.mark.asyncio
async def test_chat_stream_with_thought_tags(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        
        async def mock_stream():
            yield "<thought>Thinking...</thought>"
            yield "Done"
            
        mock_result.stream_text.return_value = mock_stream()
        # Use MagicMock for the context manager return value
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_result)
        mock_cm.__aexit__ = AsyncMock()
        mock_agent.run_stream.return_value = mock_cm
        
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        found_thought_duration = False
        for line in response.iter_lines():
            if "thought_duration" in line:
                found_thought_duration = True
                break
        assert found_thought_duration

@pytest.mark.asyncio
async def test_chat_stream_with_citations(client, mock_chat_service):
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_agent_config = MagicMock()
        mock_agent_config.require_citations = True
        mock_agent_config.provider = "openai"
        mock_agent_config.model = "gpt-4o"
        mock_agent_config.system_prompt = "test prompt"
        mock_agent_config.doc_roots = []
        mock_agent_store.get_agent.return_value = mock_agent_config
        
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        
        async def mock_stream(): yield "Answer"
        mock_result.stream_text.return_value = mock_stream()
        
        # We need to capture the deps dict passed to run_stream and modify it
        def mock_run_stream(*args, **kwargs):
            deps = kwargs.get("deps")
            if deps is not None:
                deps["citations"].append({
                    "path": "test.txt",
                    "start_line": 1,
                    "end_line": 5
                })
            return mock_result
            
        mock_agent.run_stream.side_effect = mock_run_stream
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock()
        
        response = client.post("/api/chat/stream", json={"message": "hi", "agent_id": "agent-1"})
        assert response.status_code == 200
        found_citations = False
        found_sources = False
        found_citation_link = False
        for line in response.iter_lines():
            if "citations" in line:
                found_citations = True
            if "Sources:" in line:
                found_sources = True
            if "test.txt#L1-L5" in line:
                found_citation_link = True
            if found_citations and found_sources and found_citation_link:
                break
        assert found_citations
        assert found_sources
        assert found_citation_link

@pytest.mark.asyncio
async def test_chat_stream_emits_tool_call_mismatch_when_no_tool_events(client, mock_chat_service):
    with patch.dict("os.environ", {"TOOL_CALL_MISMATCH_AUTO_RETRY_ENABLED": "false"}, clear=False), \
         patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def mock_stream():
            yield "我来帮您分析这个 PDF。"

        mock_result.stream_text.return_value = mock_stream()
        mock_result.response = MagicMock(finish_reason="tool_call")
        mock_result.usage.return_value = MagicMock(request_tokens=10, response_tokens=5, total_tokens=15)
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "分析 ar_2024_en.pdf"})
        assert response.status_code == 200
        found_tool_call_mismatch = False
        found_mismatch_message = False
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            try:
                payload = json.loads(line[6:])
            except Exception:
                continue
            if payload.get("event") == "tool_call_mismatch":
                found_tool_call_mismatch = True
            content = payload.get("content")
            if isinstance(content, str) and "模型返回了 `tool_call` 结束信号" in content:
                found_mismatch_message = True
            if found_tool_call_mismatch and found_mismatch_message:
                break
        assert found_tool_call_mismatch
        assert found_mismatch_message

@pytest.mark.asyncio
async def test_chat_stream_auto_retry_after_tool_call_mismatch(client, mock_chat_service):
    with patch.dict("os.environ", {
        "TOOL_CALL_MISMATCH_AUTO_RETRY_ENABLED": "true",
        "TOOL_CALL_MISMATCH_FALLBACK_MODEL": "gpt-4o-mini"
    }, clear=False), \
         patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None

        first_agent = MagicMock()
        second_agent = MagicMock()
        mock_agent_cls.side_effect = [first_agent, second_agent]

        first_result = MagicMock()
        async def first_stream():
            yield "先尝试处理。"
        first_result.stream_text.return_value = first_stream()
        first_result.response = MagicMock(finish_reason="tool_call")
        first_result.usage.return_value = MagicMock(request_tokens=10, response_tokens=5, total_tokens=15)
        first_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=first_result)
        first_agent.run_stream.return_value.__aexit__ = AsyncMock()

        second_result = MagicMock()
        async def second_stream():
            yield "这是重试后的最终答案。"
        second_result.stream_text.return_value = second_stream()
        second_result.response = MagicMock(finish_reason="stop")
        second_result.usage.return_value = MagicMock(request_tokens=11, response_tokens=8, total_tokens=19)
        second_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=second_result)
        second_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "root folder下都有什么文件"})
        assert response.status_code == 200
        found_tool_call_retry = False
        found_tool_call_retry_success = False
        found_tool_call_mismatch = False
        for line in response.iter_lines():
            if "tool_call_retry" in line:
                found_tool_call_retry = True
            if "tool_call_retry_success" in line:
                found_tool_call_retry_success = True
            if "tool_call_mismatch" in line:
                found_tool_call_mismatch = True
            if found_tool_call_retry and found_tool_call_retry_success:
                break
        assert found_tool_call_retry
        assert found_tool_call_retry_success
        assert not found_tool_call_mismatch
        assert second_agent.run_stream.called

@pytest.mark.asyncio
async def test_chat_stream_skip_same_model_retry_and_use_next_candidate(client, mock_chat_service):
    with patch.dict("os.environ", {
        "TOOL_CALL_MISMATCH_AUTO_RETRY_ENABLED": "true",
        "TOOL_CALL_MISMATCH_FALLBACK_MODELS": "openai/gpt-4o,deepseek/deepseek-chat"
    }, clear=False), \
         patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model") as mock_get_model, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None

        first_agent = MagicMock()
        second_agent = MagicMock()
        mock_agent_cls.side_effect = [first_agent, second_agent]

        first_result = MagicMock()
        async def first_stream():
            yield "先尝试处理。"
        first_result.stream_text.return_value = first_stream()
        first_result.response = MagicMock(finish_reason="tool_call")
        first_result.usage.return_value = MagicMock(request_tokens=10, response_tokens=5, total_tokens=15)
        first_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=first_result)
        first_agent.run_stream.return_value.__aexit__ = AsyncMock()

        second_result = MagicMock()
        async def second_stream():
            yield "跨 provider 重试成功。"
        second_result.stream_text.return_value = second_stream()
        second_result.response = MagicMock(finish_reason="stop")
        second_result.usage.return_value = MagicMock(request_tokens=12, response_tokens=7, total_tokens=19)
        second_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=second_result)
        second_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "查一下目录结构", "provider": "openai", "model": "gpt-4o"})
        assert response.status_code == 200
        found_tool_call_retry = False
        found_deepseek = False
        found_tool_call_mismatch = False
        for line in response.iter_lines():
            if "tool_call_retry" in line:
                found_tool_call_retry = True
            if "deepseek" in line:
                found_deepseek = True
            if "tool_call_mismatch" in line:
                found_tool_call_mismatch = True
            if found_tool_call_retry and found_deepseek:
                break
        assert found_tool_call_retry
        assert found_deepseek
        assert not found_tool_call_mismatch

        assert mock_get_model.call_count >= 2
        first_call_args = mock_get_model.call_args_list[0].args
        second_call_args = mock_get_model.call_args_list[1].args
        assert first_call_args == ("openai", "gpt-4o")
        assert second_call_args == ("deepseek", "deepseek-chat")

@pytest.mark.asyncio
async def test_chat_stream_emits_meta_reasoning_flags_and_envelope_sequence(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.config_service.get_model_capabilities") as mock_caps:
        mock_caps.return_value = ["reasoning"]
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def mock_stream():
            yield "Hello"

        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "hi", "provider": "openai", "model": "gpt-4o", "deep_thinking_enabled": True})
        assert response.status_code == 200

        payloads = []
        for line in response.iter_lines():
            if not isinstance(line, str) or not line.startswith("data: "):
                continue
            try:
                payloads.append(json.loads(line[6:]))
            except Exception:
                continue

        v2_payloads = [p for p in payloads if p.get("version") == "v2" and isinstance(p.get("sequence"), int)]
        assert len(v2_payloads) > 0
        sequences = [p["sequence"] for p in v2_payloads]
        assert sequences == sorted(sequences)

        meta = next(p["meta"] for p in payloads if isinstance(p, dict) and "meta" in p)
        assert meta["supports_reasoning"] is True
        assert meta["deep_thinking_enabled"] is True
        assert meta["reasoning_enabled"] is True


@pytest.mark.asyncio
async def test_chat_stream_emits_vision_meta(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.save_base64_image", return_value="/files/x.png"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.config_service.get_model_capabilities", return_value=["vision"]):
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def mock_stream():
            yield "ok"

        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post(
            "/api/chat/stream",
            json={
                "message": "what is in this image",
                "provider": "openai",
                "model": "gpt-4o",
                "images": ["data:image/png;base64,QUJDRA=="],
            },
        )
        assert response.status_code == 200

        payloads = []
        for line in response.iter_lines():
            if not isinstance(line, str) or not line.startswith("data: "):
                continue
            try:
                payloads.append(json.loads(line[6:]))
            except Exception:
                continue

        meta = next(p["meta"] for p in payloads if isinstance(p, dict) and "meta" in p)
        assert meta["supports_vision"] is True
        assert meta["vision_enabled"] is True
        assert meta["image_count"] == 1
