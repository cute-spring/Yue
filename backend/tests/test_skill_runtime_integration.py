import pytest
import json
import os
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.agent_store import AgentConfig
from app.services.skill_service import skill_registry, SkillRegistry, SkillDirectorySpec, SkillSpec, SkillRouter

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_skill_runtime_integration_auto_mode(client):
    """
    Phase 2/3 Integration: Verify that skill_mode="auto" correctly selects 
    and applies a visible skill.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Setup a temporary skill
        skill_content = """---
name: test-skill
version: 1.0.0
description: A test skill
capabilities: ["test"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:docs_read"]
---
## System Prompt
YOU ARE A TEST SKILL.
"""
        skill_path = os.path.join(tmp_dir, "test.md")
        with open(skill_path, "w") as f:
            f.write(skill_content)
        
        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()
        
            # 2. Mock Agent and Chat Flow
            payload = {
                "message": "Use the test skill.",
                "agent_id": "test-agent",
                "provider": "openai",
                "model": "gpt-4o"
            }
        
            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.Agent") as mock_agent_cls, \
                 patch("app.api.chat.chat_service") as mock_chat_service, \
                 patch("app.api.chat.tool_registry") as mock_registry:

                # Mock AgentConfig (Legacy)
                mock_agent = AgentConfig(
                    id="test-agent",
                    name="Test Agent",
                    system_prompt="YOU ARE A LEGACY AGENT.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:docs_read", "builtin:exec"], # Legacy tools
                    skill_mode="auto",
                    visible_skills=[],
                    skill_groups=["group-backend"],
                    resolved_visible_skills=["test-skill:1.0.0"]
                )
                mock_agent_store.get_agent.return_value = mock_agent
                mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

                # Mock Agent instance and its run_stream method
                mock_agent_instance = MagicMock()
                mock_agent_cls.return_value = mock_agent_instance

                mock_result = MagicMock()
                async def mock_stream_gen():
                    yield "data: " + json.dumps({"content": "Applied skill."}) + "\n\n"
                mock_result.stream_text.return_value = mock_stream_gen()
                mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
                mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

                # 3. Execution
                response = client.post("/api/chat/stream", json=payload)

                # 4. Assertions
                assert response.status_code == 200

                # Verify Agent was initialized with LAYERED system prompt
                mock_agent_cls.assert_called_once()
                _, kwargs = mock_agent_cls.call_args

                # Persona + Skill
                assert "YOU ARE A LEGACY AGENT." in kwargs["system_prompt"]
                assert "[Active Skill: test-skill]" in kwargs["system_prompt"]
                assert "YOU ARE A TEST SKILL." in kwargs["system_prompt"]

                # Verify Tool Intersection: ["builtin:docs_read", "builtin:exec"] ∩ ["builtin:docs_read"] = ["builtin:docs_read"]
                mock_registry.get_pydantic_ai_tools_for_agent.assert_called_once()
                _, reg_kwargs = mock_registry.get_pydantic_ai_tools_for_agent.call_args
                assert set(reg_kwargs["enabled_tools"]) == {"builtin:docs_read"}
                _, metrics = mock_chat_service.add_skill_effectiveness_event.call_args.args
                assert metrics["selected_group_ids"] == ["group-backend"]
                assert metrics["resolved_skill_count"] == 1
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_skill_runtime_manual_mode_requires_requested_skill(client):
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_content = """---
name: manual-skill
version: 1.0.0
description: A manual test skill
capabilities: ["manual"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:docs_read"]
---
## System Prompt
YOU ARE A MANUAL SKILL.
"""
        skill_path = os.path.join(tmp_dir, "manual.md")
        with open(skill_path, "w") as f:
            f.write(skill_content)

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            payload = {
                "message": "Use manual skill.",
                "agent_id": "manual-agent",
                "provider": "openai",
                "model": "gpt-4o",
                "requested_skill": "manual-skill:1.0.0"
            }

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.Agent") as mock_agent_cls, \
                 patch("app.api.chat.chat_service") as mock_chat_service, \
                 patch("app.api.chat.tool_registry") as mock_registry:

                mock_agent = AgentConfig(
                    id="manual-agent",
                    name="Manual Agent",
                    system_prompt="YOU ARE A LEGACY AGENT.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:docs_read", "builtin:exec"],
                    skill_mode="manual",
                    visible_skills=[],
                    skill_groups=["group-manual"],
                    resolved_visible_skills=["manual-skill:1.0.0"]
                )
                mock_agent_store.get_agent.return_value = mock_agent
                mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_instance = MagicMock()
                mock_agent_cls.return_value = mock_agent_instance

                mock_result = MagicMock()
                async def mock_stream_gen():
                    yield "data: " + json.dumps({"content": "Applied manual skill."}) + "\n\n"
                mock_result.stream_text.return_value = mock_stream_gen()
                mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
                mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

                response = client.post("/api/chat/stream", json=payload)
                assert response.status_code == 200

                _, kwargs = mock_agent_cls.call_args
                assert "[Active Skill: manual-skill]" in kwargs["system_prompt"]
                _, metrics = mock_chat_service.add_skill_effectiveness_event.call_args.args
                assert metrics["selected_group_ids"] == ["group-manual"]
                assert metrics["resolved_skill_count"] == 1

            payload_without_selection = {
                "message": "No explicit skill.",
                "agent_id": "manual-agent",
                "provider": "openai",
                "model": "gpt-4o"
            }

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.Agent") as mock_agent_cls, \
                 patch("app.api.chat.chat_service") as mock_chat_service, \
                 patch("app.api.chat.tool_registry") as mock_registry:

                mock_agent = AgentConfig(
                    id="manual-agent",
                    name="Manual Agent",
                    system_prompt="YOU ARE A LEGACY AGENT.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:docs_read", "builtin:exec"],
                    skill_mode="manual",
                    visible_skills=["manual-skill:1.0.0"]
                )
                mock_agent_store.get_agent.return_value = mock_agent
                mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_instance = MagicMock()
                mock_agent_cls.return_value = mock_agent_instance

                mock_result = MagicMock()
                async def mock_stream_gen_legacy():
                    yield "data: " + json.dumps({"content": "Legacy path."}) + "\n\n"
                mock_result.stream_text.return_value = mock_stream_gen_legacy()
                mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
                mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

                response = client.post("/api/chat/stream", json=payload_without_selection)
                assert response.status_code == 200

                _, kwargs = mock_agent_cls.call_args
                assert "[Active Skill:" not in kwargs["system_prompt"]
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_skill_runtime_no_constraints_keeps_agent_tools(client):
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_content = """---
name: unconstrained-skill
version: 1.0.0
description: A skill without constraints
capabilities: ["general"]
entrypoint: system_prompt
---
## System Prompt
YOU ARE AN UNCONSTRAINED SKILL.
"""
        skill_path = os.path.join(tmp_dir, "unconstrained.md")
        with open(skill_path, "w") as f:
            f.write(skill_content)

        skill_registry.skill_dirs = [tmp_dir]
        skill_registry.load_all()

        payload = {
            "message": "Use unconstrained skill.",
            "agent_id": "unconstrained-agent",
            "provider": "openai",
            "model": "gpt-4o"
        }

        with patch("app.api.chat.agent_store") as mock_agent_store, \
             patch("app.api.chat.Agent") as mock_agent_cls, \
             patch("app.api.chat.chat_service") as mock_chat_service, \
             patch("app.api.chat.tool_registry") as mock_registry:

            mock_agent = AgentConfig(
                id="unconstrained-agent",
                name="Unconstrained Agent",
                system_prompt="YOU ARE A LEGACY AGENT.",
                provider="openai",
                model="gpt-4o",
                enabled_tools=["builtin:docs_read", "builtin:exec"],
                skill_mode="auto",
                visible_skills=["unconstrained-skill:1.0.0"]
            )
            mock_agent_store.get_agent.return_value = mock_agent
            mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
            mock_chat_service.get_chat.return_value = None
            mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

            mock_agent_instance = MagicMock()
            mock_agent_cls.return_value = mock_agent_instance

            mock_result = MagicMock()
            async def mock_stream_gen():
                yield "data: " + json.dumps({"content": "Applied unconstrained skill."}) + "\n\n"
            mock_result.stream_text.return_value = mock_stream_gen()
            mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
            mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

            response = client.post("/api/chat/stream", json=payload)
            assert response.status_code == 200

            mock_registry.get_pydantic_ai_tools_for_agent.assert_called_once()
            _, reg_kwargs = mock_registry.get_pydantic_ai_tools_for_agent.call_args
            assert set(reg_kwargs["enabled_tools"]) == {"builtin:docs_read", "builtin:exec"}

@pytest.mark.asyncio
async def test_skill_runtime_applies_provider_overlay_when_loading_full_skill(client):
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "overlay-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: overlay-skill
version: 1.0.0
description: Overlay skill
capabilities: ["test"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:docs_read"]
---
## System Prompt
BASE PROMPT
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: overlay-skill
version: 1.0.0
description: Overlay skill
entrypoint: system_prompt
capabilities: ["test"]
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
""")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("""system_prompt: OPENAI OVERLAY PROMPT
instructions: OPENAI OVERLAY INSTRUCTIONS
constraints:
  allowed_tools: ["builtin:exec"]
""")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            payload = {
                "message": "Use the overlay skill.",
                "agent_id": "overlay-agent",
                "provider": "openai",
                "model": "gpt-4o"
            }

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.Agent") as mock_agent_cls, \
                 patch("app.api.chat.chat_service") as mock_chat_service, \
                 patch("app.api.chat.tool_registry") as mock_registry:

                mock_agent = AgentConfig(
                    id="overlay-agent",
                    name="Overlay Agent",
                    system_prompt="YOU ARE A LEGACY AGENT.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:docs_read", "builtin:exec"],
                    skill_mode="auto",
                    visible_skills=[],
                    resolved_visible_skills=["overlay-skill:1.0.0"]
                )
                mock_agent_store.get_agent.return_value = mock_agent
                mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_instance = MagicMock()
                mock_agent_cls.return_value = mock_agent_instance

                mock_result = MagicMock()
                async def mock_stream_gen():
                    yield "data: " + json.dumps({"content": "Applied overlay skill."}) + "\n\n"
                mock_result.stream_text.return_value = mock_stream_gen()
                mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
                mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

                response = client.post("/api/chat/stream", json=payload)
                assert response.status_code == 200

                _, kwargs = mock_agent_cls.call_args
                assert "OPENAI OVERLAY PROMPT" in kwargs["system_prompt"]
                assert "OPENAI OVERLAY INSTRUCTIONS" in kwargs["system_prompt"]

                _, reg_kwargs = mock_registry.get_pydantic_ai_tools_for_agent.call_args
                assert set(reg_kwargs["enabled_tools"]) == {"builtin:exec"}
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_skill_runtime_prefers_model_specific_overlay_when_available(client):
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "overlay-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: overlay-skill
version: 1.0.0
description: Overlay skill
capabilities: ["test"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:docs_read"]
---
## System Prompt
BASE PROMPT
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: overlay-skill
version: 1.0.0
description: Overlay skill
entrypoint: system_prompt
capabilities: ["test"]
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
    - provider: openai
      model: gpt-4o
      path: agents/openai.gpt-4o.yaml
""")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("""system_prompt: OPENAI PROVIDER PROMPT
constraints:
  allowed_tools: ["builtin:exec"]
""")
        with open(os.path.join(pkg_dir, "agents", "openai.gpt-4o.yaml"), "w") as f:
            f.write("""instructions: GPT4O MODEL INSTRUCTIONS
""")

        prev_layered = list(skill_registry.layered_skill_dirs)
        prev_skill_dirs = list(skill_registry.skill_dirs)
        try:
            skill_registry.layered_skill_dirs = []
            skill_registry.skill_dirs = [tmp_dir]
            skill_registry.load_all()

            payload = {
                "message": "Use the overlay skill.",
                "agent_id": "overlay-agent",
                "provider": "openai",
                "model": "gpt-4o"
            }

            with patch("app.api.chat.agent_store") as mock_agent_store, \
                 patch("app.api.chat.Agent") as mock_agent_cls, \
                 patch("app.api.chat.chat_service") as mock_chat_service, \
                 patch("app.api.chat.tool_registry") as mock_registry:

                mock_agent = AgentConfig(
                    id="overlay-agent",
                    name="Overlay Agent",
                    system_prompt="YOU ARE A LEGACY AGENT.",
                    provider="openai",
                    model="gpt-4o",
                    enabled_tools=["builtin:docs_read", "builtin:exec"],
                    skill_mode="auto",
                    visible_skills=[],
                    resolved_visible_skills=["overlay-skill:1.0.0"]
                )
                mock_agent_store.get_agent.return_value = mock_agent
                mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
                mock_chat_service.get_chat.return_value = None
                mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

                mock_agent_instance = MagicMock()
                mock_agent_cls.return_value = mock_agent_instance

                mock_result = MagicMock()
                async def mock_stream_gen():
                    yield "data: " + json.dumps({"content": "Applied model overlay skill."}) + "\n\n"
                mock_result.stream_text.return_value = mock_stream_gen()
                mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
                mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

                response = client.post("/api/chat/stream", json=payload)
                assert response.status_code == 200

                _, kwargs = mock_agent_cls.call_args
                assert "OPENAI PROVIDER PROMPT" in kwargs["system_prompt"]
                assert "GPT4O MODEL INSTRUCTIONS" in kwargs["system_prompt"]

                _, reg_kwargs = mock_registry.get_pydantic_ai_tools_for_agent.call_args
                assert set(reg_kwargs["enabled_tools"]) == {"builtin:exec"}
        finally:
            skill_registry.layered_skill_dirs = prev_layered
            skill_registry.skill_dirs = prev_skill_dirs
            skill_registry.load_all()

@pytest.mark.asyncio
async def test_skill_runtime_kill_switch_forces_legacy_path(client):
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_content = """---
name: kill-switch-skill
version: 1.0.0
description: A kill switch test skill
capabilities: ["test"]
entrypoint: system_prompt
---
## System Prompt
YOU ARE A KILL SWITCH SKILL.
"""
        skill_path = os.path.join(tmp_dir, "kill-switch.md")
        with open(skill_path, "w") as f:
            f.write(skill_content)

        skill_registry.skill_dirs = [tmp_dir]
        skill_registry.load_all()

        payload = {
            "message": "Try skill with runtime disabled.",
            "agent_id": "kill-switch-agent",
            "provider": "openai",
            "model": "gpt-4o"
        }

        with patch("app.api.chat.agent_store") as mock_agent_store, \
             patch("app.api.chat.config_service.get_feature_flags", return_value={
                 "skill_runtime_enabled": False,
                 "skill_selector_tool_enabled": True,
                 "skill_auto_mode_enabled": True
             }), \
             patch("app.api.chat.Agent") as mock_agent_cls, \
             patch("app.api.chat.chat_service") as mock_chat_service, \
             patch("app.api.chat.tool_registry") as mock_registry:

            mock_agent = AgentConfig(
                id="kill-switch-agent",
                name="Kill Switch Agent",
                system_prompt="YOU ARE A LEGACY AGENT.",
                provider="openai",
                model="gpt-4o",
                enabled_tools=["builtin:docs_read"],
                skill_mode="auto",
                visible_skills=["kill-switch-skill:1.0.0"]
            )
            mock_agent_store.get_agent.return_value = mock_agent
            mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
            mock_chat_service.get_chat.return_value = None
            mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

            mock_agent_instance = MagicMock()
            mock_agent_cls.return_value = mock_agent_instance

            mock_result = MagicMock()
            async def mock_stream_gen():
                yield "data: " + json.dumps({"content": "Legacy only."}) + "\n\n"
            mock_result.stream_text.return_value = mock_stream_gen()
            mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
            mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

            response = client.post("/api/chat/stream", json=payload)
            assert response.status_code == 200

            _, kwargs = mock_agent_cls.call_args
            assert "[Active Skill:" not in kwargs["system_prompt"]

if __name__ == "__main__":
    pytest.main([__file__])

def test_user_dir_hot_reload():
    with tempfile.TemporaryDirectory() as root_dir:
        builtin_dir = os.path.join(root_dir, "builtin")
        workspace_dir = os.path.join(root_dir, "workspace")
        user_dir = os.path.join(root_dir, "user")
        os.makedirs(builtin_dir, exist_ok=True)
        os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(user_dir, exist_ok=True)

        registry = SkillRegistry()
        registry.set_layered_skill_dirs([
            SkillDirectorySpec(layer="builtin", path=builtin_dir),
            SkillDirectorySpec(layer="workspace", path=workspace_dir),
            SkillDirectorySpec(layer="user", path=user_dir),
        ])
        registry.load_all()
        assert registry.get_skill("hot-reload-skill", "1.0.0") is None

        registry.start_runtime_watch(layer="user", debounce_ms=200)
        try:
            skill_pkg = os.path.join(user_dir, "hot-reload-skill")
            os.makedirs(skill_pkg, exist_ok=True)
            with open(os.path.join(skill_pkg, "SKILL.md"), "w") as f:
                f.write("""---
name: hot-reload-skill
version: 1.0.0
description: hot reload
capabilities: ["hot"]
entrypoint: system_prompt
---
## System Prompt
HOT RELOAD
""")

            deadline = 4.0
            elapsed = 0.0
            while elapsed < deadline:
                if registry.get_skill("hot-reload-skill", "1.0.0") is not None:
                    break
                import time
                time.sleep(0.2)
                elapsed += 0.2
            assert registry.get_skill("hot-reload-skill", "1.0.0") is not None
        finally:
            registry.stop_runtime_watch()

def test_source_layer_metrics():
    import app.services.chat_service as chat_service_module
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as td:
        db_file = os.path.join(td, "yue.db")
        test_engine = create_engine(f"sqlite:///{db_file}")
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        
        with patch("app.services.chat_service.engine", test_engine), \
             patch("app.services.chat_service.SessionLocal", TestingSessionLocal), \
             patch("app.services.chat_service.DATA_DIR", td):
             
            service = chat_service_module.ChatService()
            chat = service.create_chat()
            service.add_skill_effectiveness_event(chat.id, {
                "reason_code": "skill_selected",
                "selection_source": "explicit",
                "fallback_used": False,
                "selected_skill": {"name": "planner", "version": "1.0.0"},
                "selected_skill_source_layer": "user",
                "override_hit": True,
            })
            conn = sqlite3.connect(db_file)
            try:
                row = conn.execute(
                    "SELECT selected_skill_source_layer, override_hit FROM skill_effectiveness_events ORDER BY id DESC LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
            assert row is not None
            assert row[0] == "user"
            assert row[1] == 1
            
        test_engine.dispose()


def test_visible_skills_resolve_from_groups_and_extra_with_dedupe():
    registry = SkillRegistry()
    registry.register(
        SkillSpec(
            name="release-test-planner",
            version="1.0.0",
            description="planner",
            capabilities=["planning"],
            entrypoint="system_prompt",
            system_prompt="planner",
        )
    )
    registry.register(
        SkillSpec(
            name="backend-api-debugger",
            version="1.0.0",
            description="debugger",
            capabilities=["debug"],
            entrypoint="system_prompt",
            system_prompt="debugger",
        )
    )

    router = SkillRouter(registry)
    agent = AgentConfig(
        name="Group Agent",
        system_prompt="Agent prompt",
        skill_groups=["group-backend"],
        extra_visible_skills=["backend-api-debugger:1.0.0"],
        visible_skills=["release-test-planner:1.0.0", "backend-api-debugger:1.0.0"],
    )

    with patch("app.services.skill_service.skill_group_store") as mock_group_store:
        mock_group_store.get_skill_refs_by_group_ids.return_value = [
            "release-test-planner:1.0.0",
            "backend-api-debugger:1.0.0",
        ]
        visible = router.get_visible_skills(agent)

    refs = [f"{s.name}:{s.version}" for s in visible]
    assert refs == ["release-test-planner:1.0.0", "backend-api-debugger:1.0.0"]


def test_visible_skills_legacy_fallback_without_groups():
    registry = SkillRegistry()
    registry.register(
        SkillSpec(
            name="release-test-planner",
            version="1.0.0",
            description="planner",
            capabilities=["planning"],
            entrypoint="system_prompt",
            system_prompt="planner",
        )
    )
    router = SkillRouter(registry)
    agent = AgentConfig(
        name="Legacy Agent",
        system_prompt="Agent prompt",
        visible_skills=["release-test-planner:1.0.0"],
    )
    visible = router.get_visible_skills(agent)
    assert len(visible) == 1
    assert visible[0].name == "release-test-planner"
