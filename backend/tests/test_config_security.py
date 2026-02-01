import unittest
import requests

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

if __name__ == "__main__":
    unittest.main()
