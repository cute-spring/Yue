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
        name_counts = {}
        for t in tools:
            name_counts[t["name"]] = name_counts.get(t["name"], 0) + 1
        candidates = [t for t in tools if name_counts.get(t["name"]) == 1]
        if not candidates:
            self.skipTest("No uniquely-named MCP tools available")
        target = candidates[0]
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
        self.assertIn(target["id"], agent.get("enabled_tools", []))

        r = requests.put(f"{BASE}/api/agents/{aid}", json={
            "enabled_tools": [target["name"]]
        })
        self.assertEqual(r.status_code, 200)
        updated = r.json()
        self.assertIn(target["id"], updated.get("enabled_tools", []))
        r = requests.get(f"{BASE}/api/agents/")
        self.assertEqual(r.status_code, 200)
        agents = r.json()
        created = [a for a in agents if a.get("id") == aid][0]
        self.assertIn(target["id"], created.get("enabled_tools", []))
        requests.delete(f"{BASE}/api/agents/{aid}")

if __name__ == "__main__":
    unittest.main()
