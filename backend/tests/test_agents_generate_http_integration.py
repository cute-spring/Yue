import unittest
import os
import requests


class TestAgentsGenerateHttpIntegration(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("RUN_HTTP_INTEGRATION_TESTS") == "1",
        "Set RUN_HTTP_INTEGRATION_TESTS=1 to enable HTTP integration tests.",
    )
    def test_generate_over_http_with_deepseek(self):
        base_url = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8003")
        r = requests.post(
            f"{base_url}/api/agents/generate",
            json={
                "description": "Create an agent that reviews pull requests and suggests actionable improvements.",
                "provider": "deepseek",
                "model": "deepseek-reasoner",
                "existing_tools": [],
                "update_tools": True,
            },
            timeout=90,
        )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(isinstance(data.get("name"), str) and data["name"].strip())
        self.assertTrue(isinstance(data.get("system_prompt"), str) and data["system_prompt"].strip())
        self.assertTrue(isinstance(data.get("enabled_tools"), list))


if __name__ == "__main__":
    unittest.main()

