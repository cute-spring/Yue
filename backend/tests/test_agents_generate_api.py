import unittest
import os
import sys
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import contextlib

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.api import agents as agents_module


class _FakeStreamResult:
    def __init__(self, text: str):
        self._text = text

    async def stream_text(self):
        yield self._text


class _FakeRunStreamCtx:
    def __init__(self, text: str):
        self._text = text

    async def __aenter__(self):
        return _FakeStreamResult(self._text)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeAgent:
    def __init__(self, model, system_prompt: str = ""):
        self.model = model
        self.system_prompt = system_prompt

    def run_stream(self, user_prompt: str):
        payload = {
            "name": "Code Reviewer",
            "system_prompt": "Role: Senior reviewer\nScope: frontend only\nWorkflow: step by step\nOutput format: bullet list\nProhibitions: no secrets",
            "enabled_tools": ["filesystem:list", "builtin:docs_search"],
            "tool_reasons": {
                "filesystem:list": "Scan repository structure quickly",
                "builtin:docs_search": "Search internal docs for conventions",
            },
        }
        return _FakeRunStreamCtx(text=str(payload).replace("'", '"'))


@contextlib.contextmanager
def _patched_generate_deps(tools: list[dict]):
    async def _fake_get_available_tools():
        return tools

    with patch.object(agents_module, "Agent", FakeAgent), patch.object(
        agents_module, "get_model", lambda provider, model: {"provider": provider, "model": model}
    ), patch.object(agents_module.mcp_manager, "get_available_tools", _fake_get_available_tools):
        yield


class TestAgentsGenerateAPI(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(agents_module.router, prefix="/api/agents")
        self.client = TestClient(app)

    def test_generate_requires_description(self):
        tools = [{"id": "builtin:docs_search", "name": "docs_search", "server": "builtin", "description": ""}]
        with _patched_generate_deps(tools):
            r = self.client.post("/api/agents/generate", json={"description": ""})
            self.assertEqual(r.status_code, 400)

    def test_generate_returns_draft_fields(self):
        tools = [
            {"id": "filesystem:list", "name": "list", "server": "filesystem", "description": "List files"},
            {"id": "builtin:docs_search", "name": "docs_search", "server": "builtin", "description": "Search docs"},
        ]
        with _patched_generate_deps(tools):
            r = self.client.post(
                "/api/agents/generate",
                json={
                    "description": "I want an agent to review PRs",
                    "provider": "dummy",
                    "model": "d1",
                    "existing_tools": [],
                    "update_tools": True,
                },
            )
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("name", data)
            self.assertIn("system_prompt", data)
            self.assertIn("enabled_tools", data)
            self.assertIn("recommended_tools", data)
            self.assertIn("tool_reasons", data)
            self.assertIn("tool_risks", data)
            self.assertTrue(isinstance(data["recommended_tools"], list))
            self.assertTrue("filesystem:list" in data["recommended_tools"])
            self.assertEqual(data["tool_risks"].get("filesystem:list"), "read")

    def test_update_tools_false_keeps_existing_tools(self):
        tools = [
            {"id": "filesystem:list", "name": "list", "server": "filesystem", "description": "List files"},
            {"id": "builtin:docs_search", "name": "docs_search", "server": "builtin", "description": "Search docs"},
        ]
        with _patched_generate_deps(tools):
            r = self.client.post(
                "/api/agents/generate",
                json={
                    "description": "Generate but keep my tools",
                    "provider": "dummy",
                    "model": "d1",
                    "existing_tools": ["builtin:docs_search"],
                    "update_tools": False,
                },
            )
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["enabled_tools"], ["builtin:docs_search"])


if __name__ == "__main__":
    unittest.main()
