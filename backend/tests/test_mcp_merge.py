import unittest
import requests

BASE = "http://127.0.0.1:8003"

from _server import ensure_backend_running

ensure_backend_running(BASE)

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

    def test_mcp_config_validation_error_format(self):
        r = requests.post(f"{BASE}/api/mcp/", json=[{"name": "bad-one"}])
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("detail", data)
        detail = data["detail"]
        self.assertEqual(detail.get("error"), "validation_error")
        issues = detail.get("issues")
        self.assertIsInstance(issues, list)
        self.assertTrue(any("command" in (i.get("path") or "") for i in issues))

    def test_mcp_config_duplicate_names(self):
        r = requests.post(
            f"{BASE}/api/mcp/",
            json=[
                {"name": "dup", "transport": "stdio", "command": "npx", "args": ["-y", "mcp-server-example"], "enabled": True},
                {"name": "dup", "transport": "stdio", "command": "npx", "args": ["-y", "mcp-server-example"], "enabled": True},
            ],
        )
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("detail", data)
        detail = data["detail"]
        self.assertEqual(detail.get("error"), "validation_error")
        issues = detail.get("issues")
        self.assertIsInstance(issues, list)
        self.assertTrue(any("duplicate server name" in (i.get("message") or "") for i in issues))

if __name__ == "__main__":
    unittest.main()
