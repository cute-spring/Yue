import unittest
import requests


BASE = "http://127.0.0.1:8003"
TRACE_HEADER = "X-Request-Id"

from _server import ensure_backend_running

ensure_backend_running(BASE)


class TestTraceIdHeaders(unittest.TestCase):
    def test_trace_id_echo(self):
        trace_id = "test-trace-id-123"
        r = requests.get(f"{BASE}/api/mcp/status", headers={TRACE_HEADER: trace_id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get(TRACE_HEADER), trace_id)

    def test_trace_id_generated(self):
        r = requests.get(f"{BASE}/api/mcp/status")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers.get(TRACE_HEADER))


if __name__ == "__main__":
    unittest.main()
