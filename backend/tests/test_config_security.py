import os
import sys
import unittest
import requests

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.config_service import config_service

BASE = "http://127.0.0.1:8003"

class TestConfigSecurity(unittest.TestCase):
    def test_llm_redaction_and_update(self):
        r = requests.post(f"{BASE}/api/config/llm", json={
            "openai_model": "gpt-4o",
            "openai_api_key": "****masked****"
        })
        self.assertEqual(r.status_code, 200)
        r = requests.get(f"{BASE}/api/config/llm")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("openai_model"), "gpt-4o")
        if "openai_api_key" in data:
            self.assertEqual(data.get("openai_api_key"), "")

    def test_doc_access_getter_filters(self):
        original = config_service._config
        try:
            config_service._config = {
                "doc_access": {
                    "allow_roots": ["/allowed", "", None, 1],
                    "deny_roots": ["/denied", " "]
                }
            }
            data = config_service.get_doc_access()
            self.assertEqual(data.get("allow_roots"), ["/allowed"])
            self.assertEqual(data.get("deny_roots"), ["/denied"])
        finally:
            config_service._config = original

    def test_doc_access_endpoint(self):
        r = requests.get(f"{BASE}/api/config/doc_access")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("allow_roots", data)
        self.assertIn("deny_roots", data)
        self.assertIsInstance(data.get("allow_roots"), list)
        self.assertIsInstance(data.get("deny_roots"), list)

if __name__ == "__main__":
    unittest.main()
