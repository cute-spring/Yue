import unittest
import requests

BASE = "http://127.0.0.1:8003"

class TestAgentsNormalization(unittest.TestCase):
    def test_normalize_enabled_tools(self):
        r = requests.get(f"{BASE}/api/agents/")
        self.assertEqual(r.status_code, 200)
        agents = r.json()
        self.assertTrue(any(a.get("id") == "builtin-docs" for a in agents))

        r = requests.get(f"{BASE}/api/mcp/tools")
        self.assertEqual(r.status_code, 200)
        tools = r.json()
        if not tools:
            self.skipTest("No MCP tools available")
        target = tools[0]
        r = requests.post(f"{BASE}/api/agents/", json={
            "name": "ToolTester",
            "system_prompt": "Test tools.",
            "provider": "openai",
            "model": "gpt-4o",
            "enabled_tools": [target["name"]]
        })
        self.assertEqual(r.status_code, 200)
        agent = r.json()
        aid = agent.get("id")
        self.assertTrue(any(x == target["id"] or x == target["name"] for x in agent.get("enabled_tools", [])))
        r = requests.get(f"{BASE}/api/agents/")
        self.assertEqual(r.status_code, 200)
        agents = r.json()
        created = [a for a in agents if a.get("id") == aid][0]
        self.assertTrue(any(x == target["id"] or x == target["name"] for x in created.get("enabled_tools", [])))
        requests.delete(f"{BASE}/api/agents/{aid}")

if __name__ == "__main__":
    unittest.main()
