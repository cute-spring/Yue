import unittest
import os
import sys
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.api import agents as agents_module


class TestAgentsGenerateLiveDeepSeek(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("RUN_LIVE_LLM_TESTS") == "1",
        "Set RUN_LIVE_LLM_TESTS=1 to enable live LLM tests.",
    )
    @unittest.skipUnless(
        os.environ.get("DEEPSEEK_API_KEY"),
        "DEEPSEEK_API_KEY is required for live DeepSeek tests.",
    )
    def test_generate_with_real_deepseek(self):
        api_key = os.environ["DEEPSEEK_API_KEY"]

        async def _fake_get_available_tools():
            return [
                {"id": "builtin:docs_search_markdown", "name": "docs_search_markdown", "server": "builtin", "description": "Search Yue/docs markdown"},
                {"id": "builtin:docs_read_markdown", "name": "docs_read_markdown", "server": "builtin", "description": "Read Yue/docs markdown"},
                {"id": "filesystem:list", "name": "list", "server": "filesystem", "description": "List files"},
            ]

        def _fake_llm_config():
            return {
                "deepseek_api_key": api_key,
                "deepseek_model": "deepseek-reasoner",
            }

        app = FastAPI()
        app.include_router(agents_module.router, prefix="/api/agents")
        client = TestClient(app)

        with patch.object(agents_module.mcp_manager, "get_available_tools", _fake_get_available_tools), patch(
            "app.services.model_factory.config_service.get_llm_config", _fake_llm_config
        ):
            r = client.post(
                "/api/agents/generate",
                json={
                    "description": "Create an agent that reviews pull requests and suggests actionable improvements.",
                    "provider": "deepseek",
                    "model": "deepseek-reasoner",
                    "existing_tools": [],
                    "update_tools": True,
                },
                timeout=60,
            )

        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(isinstance(data.get("name"), str) and data["name"].strip())
        self.assertLessEqual(len(data["name"]), 80)

        self.assertTrue(isinstance(data.get("system_prompt"), str) and data["system_prompt"].strip())
        self.assertGreaterEqual(len(data["system_prompt"]), 60)
        self.assertLessEqual(len(data["system_prompt"]), 6000)

        enabled_tools = data.get("enabled_tools")
        recommended_tools = data.get("recommended_tools")
        tool_reasons = data.get("tool_reasons")
        tool_risks = data.get("tool_risks")

        self.assertTrue(isinstance(enabled_tools, list))
        self.assertTrue(isinstance(recommended_tools, list))
        self.assertTrue(isinstance(tool_reasons, dict))
        self.assertTrue(isinstance(tool_risks, dict))

        self.assertLessEqual(len(recommended_tools), 6)
        self.assertEqual(enabled_tools, recommended_tools)

        available = {"builtin:docs_search_markdown", "builtin:docs_read_markdown", "filesystem:list"}
        for tid in recommended_tools:
            self.assertTrue(isinstance(tid, str) and tid)
            self.assertIn(tid, available)

        for k, v in tool_reasons.items():
            self.assertIn(k, set(recommended_tools))
            self.assertTrue(isinstance(v, str) and v.strip())
            self.assertGreaterEqual(len(v.strip()), 4)
            self.assertLessEqual(len(v.strip()), 160)

        allowed_risk = {"read", "write", "network", "unknown"}
        for tid in recommended_tools:
            self.assertIn(tid, tool_risks)
            self.assertIn(tool_risks.get(tid), allowed_risk)

        prompt_lc = data["system_prompt"].lower()
        categories = [
            ("role", ["role", "你是", "角色"]),
            ("scope", ["scope", "boundary", "边界", "范围"]),
            ("workflow", ["workflow", "step", "steps", "流程", "步骤"]),
            ("output", ["output", "format", "输出", "格式"]),
            ("prohibitions", ["prohibit", "forbid", "禁止", "不要", "禁忌"]),
        ]
        matched = 0
        for _, keys in categories:
            if any(k in prompt_lc for k in keys):
                matched += 1
        self.assertGreaterEqual(matched, 3)


if __name__ == "__main__":
    unittest.main()
