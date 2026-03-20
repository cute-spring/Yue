import unittest

import requests

BASE = "http://127.0.0.1:8003"


def _backend_available() -> bool:
    try:
        r = requests.get(f"{BASE}/api/mcp/status", timeout=1)
        return r.status_code >= 200
    except Exception:
        return False


class TestExportApiIntegration(unittest.TestCase):
    def test_txt_and_docx_export(self):
        if not _backend_available():
            self.skipTest("Backend not running")

        payload = {"content": "# Title\n\n- one\n- two", "format": "txt"}
        txt_resp = requests.post(f"{BASE}/api/export", json=payload, timeout=10)
        self.assertEqual(txt_resp.status_code, 200)
        self.assertIn("text/plain", txt_resp.headers.get("content-type", ""))
        self.assertIn("Title", txt_resp.text)

        payload["format"] = "docx"
        docx_resp = requests.post(f"{BASE}/api/export", json=payload, timeout=10)
        self.assertEqual(docx_resp.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_resp.headers.get("content-type", ""),
        )
        self.assertTrue(docx_resp.content.startswith(b"PK"))
