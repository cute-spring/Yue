import unittest
import requests

BASE = "http://127.0.0.1:8003"

class TestMcpAndModels(unittest.TestCase):
    def test_mcp_status_and_tools(self):
        r = requests.get(f"{BASE}/api/mcp/status")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        r2 = requests.get(f"{BASE}/api/mcp/tools")
        self.assertEqual(r2.status_code, 200)
        tools = r2.json()
        if tools:
            self.assertIn("id", tools[0])
            self.assertIn("name", tools[0])

    def test_builtin_tools_visible_in_tools_api(self):
        r = requests.get(f"{BASE}/api/mcp/tools")
        self.assertEqual(r.status_code, 200)
        tools = r.json()
        ids = {t.get("id") for t in tools if isinstance(t, dict)}
        expected = {
            "builtin:docs_search_markdown",
            "builtin:docs_read_markdown",
            "builtin:get_current_time",
            "builtin:notebook_create_note",
            "builtin:notebook_list_notes",
            "builtin:notebook_read_note",
            "builtin:notebook_update_note",
            "builtin:chat_list_sessions",
            "builtin:chat_list_messages",
            "builtin:chat_search_messages",
            "builtin:mcp_get_status",
            "builtin:mcp_list_tools",
        }
        self.assertTrue(expected.issubset(ids))

    def test_mcp_tools_stable_ids_and_dedup(self):
        r1 = requests.get(f"{BASE}/api/mcp/tools")
        self.assertEqual(r1.status_code, 200)
        tools1 = r1.json()

        r2 = requests.get(f"{BASE}/api/mcp/tools")
        self.assertEqual(r2.status_code, 200)
        tools2 = r2.json()

        ids1 = []
        for t in tools1:
            self.assertIn("id", t)
            self.assertIn("name", t)
            self.assertIn("server", t)
            tool_id = t["id"]
            server = t["server"]
            name = t["name"]
            self.assertEqual(tool_id, f"{server}:{name}")
            server_in_id, name_in_id = tool_id.split(":", 1)
            self.assertEqual(server_in_id, server)
            self.assertEqual(name_in_id, name)
            ids1.append(tool_id)

        self.assertEqual(len(ids1), len(set(ids1)))
        self.assertEqual(set(ids1), {t["id"] for t in tools2})

    def test_mcp_reload_stable(self):
        for _ in range(3):
            r = requests.post(f"{BASE}/api/mcp/reload")
            self.assertEqual(r.status_code, 200)

    def test_models_provider_test(self):
        for name in ["openai", "gemini", "deepseek", "ollama"]:
            r = requests.post(f"{BASE}/api/models/test/{name}", json={})
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("ok", data)

if __name__ == "__main__":
    unittest.main()
