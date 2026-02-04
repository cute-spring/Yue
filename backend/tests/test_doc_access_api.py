import json
import os
import tempfile
import time
import unittest

import requests

from _server import ensure_backend_running

BASE = "http://127.0.0.1:8003"

ensure_backend_running(BASE)


def _collect_sse(url: str, payload: dict, timeout_s: float = 20.0) -> list[dict]:
    r = requests.post(url, json=payload, stream=True, timeout=timeout_s)
    r.raise_for_status()
    events: list[dict] = []
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
            events.append(data)
        if time.time() - start > timeout_s:
            break
    return events


class TestDocAccessApi(unittest.TestCase):
    def test_external_doc_root_requires_allowlist_and_respects_denylist(self):
        with tempfile.TemporaryDirectory() as tmp:
            external_docs = os.path.join(tmp, "external_docs")
            os.makedirs(external_docs, exist_ok=True)
            with open(os.path.join(external_docs, "alpha.md"), "w", encoding="utf-8") as f:
                f.write("Alpha External Doc\n")

            r = requests.post(f"{BASE}/api/config/doc_access", json={"allow_roots": [], "deny_roots": []})
            self.assertEqual(r.status_code, 200)

            agent = {
                "name": "ExternalDocsTester",
                "system_prompt": "Use docs tools.",
                "provider": "openai",
                "model": "gpt-4o",
                "enabled_tools": ["builtin:docs_search_markdown", "builtin:docs_read_markdown"],
                "doc_root": external_docs,
            }
            created = requests.post(f"{BASE}/api/agents/", json=agent)
            self.assertEqual(created.status_code, 200)
            agent_id = created.json().get("id")
            self.assertTrue(agent_id)

            try:
                events = _collect_sse(
                    f"{BASE}/api/chat/stream",
                    {
                        "message": "Alpha External Doc",
                        "agent_id": agent_id,
                        "provider": "__docretriever__",
                        "model": "docretriever",
                    },
                    timeout_s=20.0,
                )
                errors = [e.get("error") for e in events if isinstance(e.get("error"), str)]
                self.assertTrue(any("root is not allowed" in e for e in errors))

                r = requests.post(f"{BASE}/api/config/doc_access", json={"allow_roots": [external_docs], "deny_roots": []})
                self.assertEqual(r.status_code, 200)

                events = _collect_sse(
                    f"{BASE}/api/chat/stream",
                    {
                        "message": "Alpha External Doc",
                        "agent_id": agent_id,
                        "provider": "__docretriever__",
                        "model": "docretriever",
                    },
                    timeout_s=20.0,
                )
                errors = [e.get("error") for e in events if isinstance(e.get("error"), str)]
                self.assertFalse(errors)
                citations_events = [e.get("citations") for e in events if isinstance(e.get("citations"), list)]
                citations = citations_events[-1] if citations_events else []
                self.assertTrue(any(isinstance(c, dict) and str(c.get("path", "")).endswith("alpha.md") for c in citations))

                r = requests.post(
                    f"{BASE}/api/config/doc_access",
                    json={"allow_roots": [external_docs], "deny_roots": [external_docs]},
                )
                self.assertEqual(r.status_code, 200)

                events = _collect_sse(
                    f"{BASE}/api/chat/stream",
                    {
                        "message": "Alpha External Doc",
                        "agent_id": agent_id,
                        "provider": "__docretriever__",
                        "model": "docretriever",
                    },
                    timeout_s=20.0,
                )
                errors = [e.get("error") for e in events if isinstance(e.get("error"), str)]
                self.assertTrue(any("root is denied" in e for e in errors))
            finally:
                requests.delete(f"{BASE}/api/agents/{agent_id}")
                requests.post(f"{BASE}/api/config/doc_access", json={"allow_roots": [], "deny_roots": []})


if __name__ == "__main__":
    unittest.main()

