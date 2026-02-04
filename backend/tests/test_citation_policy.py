import json
import time
import unittest

import requests

from _server import ensure_backend_running

BASE = "http://127.0.0.1:8003"

ensure_backend_running(BASE)


def _collect_sse_text(url: str, payload: dict, timeout_s: float = 25.0, headers: dict | None = None) -> dict:
    r = requests.post(url, json=payload, stream=True, timeout=timeout_s, headers=headers)
    r.raise_for_status()
    content = ""
    citations = None
    gaps = None
    errors = []
    start = time.time()
    for raw in r.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("data: "):
            continue
        data = json.loads(line[6:])
        if isinstance(data, dict):
            if isinstance(data.get("content"), str):
                content += data["content"]
            if isinstance(data.get("citations"), list):
                citations = data["citations"]
            if isinstance(data.get("gaps"), dict):
                gaps = data["gaps"]
            if data.get("error"):
                errors.append(str(data["error"]))
        if time.time() - start > timeout_s:
            break
    return {"content": content, "citations": citations, "gaps": gaps, "errors": errors}


class TestCitationPolicy(unittest.TestCase):
    def test_docs_agent_hallucination_is_replaced_by_no_evidence(self):
        result = _collect_sse_text(
            f"{BASE}/api/chat/stream",
            {
                "message": "给我一个结论",
                "agent_id": "builtin-docs",
                "provider": "__dochallucinate__",
                "model": "dochallucinate",
            },
            timeout_s=15.0,
        )
        self.assertFalse(result["errors"])
        self.assertIn("未在已配置的文档范围内找到可引用的依据", result["content"])
        self.assertNotIn("没有引用的结论性回答", result["content"])
        self.assertIsInstance(result["gaps"], dict)
        self.assertEqual(result["gaps"].get("kind"), "no_evidence")

    def test_docmain_appends_citations_to_text(self):
        result = _collect_sse_text(
            f"{BASE}/api/chat/stream",
            {
                "message": "Obsidian 插件",
                "agent_id": "builtin-doc-orchestrator",
                "provider": "__docmain__",
                "model": "docmain",
            },
            timeout_s=25.0,
            headers={"X-Request-Id": "trace-doc-5"},
        )
        self.assertFalse(result["errors"])
        self.assertIn("引用：", result["content"])
        self.assertIn("/backend/tests/fixtures/doc_agent/alpha.md", result["content"])
        self.assertTrue(result["citations"])
        self.assertIsNone(result["gaps"])


if __name__ == "__main__":
    unittest.main()
