import unittest
import requests

BASE = "http://127.0.0.1:8003"

class TestMcpMerge(unittest.TestCase):
    def test_upsert_configs(self):
        r = requests.get(f"{BASE}/api/mcp/")
        self.assertEqual(r.status_code, 200)
        before = r.json()
        names_before = {c.get("name") for c in before}

        new_cfg = [{
            "name": "example-server",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-server-example"],
            "enabled": True
        }]
        r = requests.post(f"{BASE}/api/mcp/", json=new_cfg)
        self.assertEqual(r.status_code, 200)
        r = requests.get(f"{BASE}/api/mcp/")
        self.assertEqual(r.status_code, 200)
        after = r.json()
        names_after = {c.get("name") for c in after}
        self.assertIn("example-server", names_after)
        self.assertTrue(names_before.issubset(names_after))

if __name__ == "__main__":
    unittest.main()
