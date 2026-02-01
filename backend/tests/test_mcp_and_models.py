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

    def test_models_provider_test(self):
        for name in ["openai", "gemini", "deepseek", "ollama"]:
            r = requests.post(f"{BASE}/api/models/test/{name}", json={})
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("ok", data)

if __name__ == "__main__":
    unittest.main()
