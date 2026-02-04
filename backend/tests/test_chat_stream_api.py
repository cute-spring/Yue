import unittest
import requests
import json
import time

BASE = "http://127.0.0.1:8003"

from _server import ensure_backend_running

ensure_backend_running(BASE)


def _collect_sse(url: str, payload: dict, timeout_s: float = 15.0, headers: dict | None = None) -> dict:
    r = requests.post(url, json=payload, stream=True, timeout=timeout_s, headers=headers)
    r.raise_for_status()
    chat_id = None
    trace_id = None
    content = ""
    thought_duration = None
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
            if "chat_id" in data and data["chat_id"]:
                chat_id = data["chat_id"]
            if "trace_id" in data and data["trace_id"]:
                trace_id = data["trace_id"]
            if "content" in data and isinstance(data["content"], str):
                content += data["content"]
            if "thought_duration" in data:
                thought_duration = data["thought_duration"]
            if "error" in data and data["error"]:
                errors.append(str(data["error"]))
        if time.time() - start > timeout_s:
            break

    return {
        "chat_id": chat_id,
        "trace_id": trace_id,
        "content": content,
        "thought_duration": thought_duration,
        "errors": errors,
    }

def _collect_sse_events(url: str, payload: dict, timeout_s: float = 20.0, headers: dict | None = None) -> list[dict]:
    r = requests.post(url, json=payload, stream=True, timeout=timeout_s, headers=headers)
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


class TestChatStreamApi(unittest.TestCase):
    def test_chat_stream_guard_returns_final_text(self):
        result = _collect_sse(
            f"{BASE}/api/chat/stream",
            {
                "message": "ping",
                "provider": "__guard__",
                "model": "guard",
            },
        )
        self.assertIsInstance(result["chat_id"], str)
        self.assertTrue(result["chat_id"])
        self.assertIsInstance(result["trace_id"], str)
        self.assertTrue(result["trace_id"])
        self.assertEqual(result["errors"], [])
        self.assertIn("OK", result["content"])
        self.assertNotIn("guard_detected_forced_thought_injection", result["content"])

    def test_recent_chat_titles_available_via_history(self):
        created_titles = []
        for i in range(12):
            title = f"API Test Chat Title {i}"
            created_titles.append(title)
            result = _collect_sse(
                f"{BASE}/api/chat/stream",
                {
                    "message": title,
                    "provider": "__guard__",
                    "model": "guard",
                },
            )
            self.assertIsInstance(result["chat_id"], str)

        r = requests.get(f"{BASE}/api/chat/history", timeout=10.0)
        self.assertEqual(r.status_code, 200)
        chats = r.json()
        self.assertIsInstance(chats, list)
        titles = [c.get("title") for c in chats[:10] if isinstance(c, dict)]

        for t in created_titles[-10:]:
            self.assertIn(t, titles)

    def test_chat_stream_merges_task_events_when_model_calls_task_tool(self):
        events = _collect_sse_events(
            f"{BASE}/api/chat/stream",
            {
                "message": "run deterministic task",
                "provider": "__toolcall__",
                "model": "toolcall",
            },
            timeout_s=25.0,
        )

        chat_id = None
        task_events = []
        content = ""

        for e in events:
            if "chat_id" in e and isinstance(e["chat_id"], str) and e["chat_id"]:
                chat_id = e["chat_id"]
            if e.get("type") == "task_event":
                task_events.append(e)
            if "content" in e and isinstance(e["content"], str):
                content += e["content"]

        self.assertIsInstance(chat_id, str)
        self.assertTrue(chat_id)
        self.assertTrue(any(t.get("status") == "started" for t in task_events))
        self.assertTrue(any(t.get("status") == "running" for t in task_events))
        self.assertTrue(any(t.get("status") == "completed" for t in task_events))
        self.assertIn("OK", content)

        completed = next((t for t in task_events if t.get("status") == "completed"), None)
        self.assertIsInstance(completed, dict)
        child_chat_id = completed.get("child_chat_id")
        self.assertIsInstance(child_chat_id, str)
        self.assertTrue(child_chat_id)

        c = requests.get(f"{BASE}/api/chat/{child_chat_id}", timeout=10.0)
        self.assertEqual(c.status_code, 200)
        child = c.json()
        self.assertEqual(child.get("parent_id"), chat_id)

    def test_chat_stream_includes_citations_from_doc_retriever_subtask(self):
        headers = {"X-Request-Id": "trace-doc-1"}
        events = _collect_sse_events(
            f"{BASE}/api/chat/stream",
            {
                "message": "Obsidian 插件",
                "agent_id": "builtin-doc-orchestrator",
                "provider": "__docmain__",
                "model": "docmain",
            },
            timeout_s=25.0,
            headers=headers,
        )

        chat_id = None
        trace_id = None
        task_events = []
        citations = []

        for e in events:
            if "chat_id" in e and isinstance(e["chat_id"], str) and e["chat_id"]:
                chat_id = e["chat_id"]
            if "trace_id" in e and isinstance(e["trace_id"], str) and e["trace_id"]:
                trace_id = e["trace_id"]
            if e.get("type") == "task_event":
                task_events.append(e)
            if "citations" in e and isinstance(e["citations"], list):
                citations = e["citations"]

        self.assertIsInstance(chat_id, str)
        self.assertTrue(chat_id)
        self.assertEqual(trace_id, "trace-doc-1")
        self.assertTrue(all(t.get("trace_id") == "trace-doc-1" for t in task_events))
        self.assertTrue(any(t.get("status") == "started" for t in task_events))
        self.assertTrue(any(t.get("status") == "completed" for t in task_events))

        self.assertIsInstance(citations, list)
        self.assertTrue(citations)
        alpha = next((c for c in citations if isinstance(c, dict) and str(c.get("path", "")).endswith("/backend/tests/fixtures/doc_agent/alpha.md")), None)
        self.assertIsInstance(alpha, dict)
        self.assertIn("Obsidian", alpha.get("snippet") or "")


if __name__ == "__main__":
    unittest.main()
