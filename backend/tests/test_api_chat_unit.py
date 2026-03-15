import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.services.skill_service import SkillSpec
from app.services.agent_store import AgentConfig

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
         patch("app.api.chat.validate_sse_payload") as mock_validate:
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
         patch("app.api.chat.validate_sse_payload") as mock_validate:
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

def test_estimate_tokens():
    from app.api.chat import estimate_tokens
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcdef") == 2

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
            "images": ["data:image/png;base64,xxx"],
            "chat_id": "chat-id"
        })
        assert response.status_code == 200
        mock_save.assert_called_once()
        mock_load.assert_called_once()

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
