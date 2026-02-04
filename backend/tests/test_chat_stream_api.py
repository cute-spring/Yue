import unittest
import requests
import json
import time

BASE = "http://127.0.0.1:8003"


def _collect_sse(url: str, payload: dict, timeout_s: float = 15.0) -> dict:
    r = requests.post(url, json=payload, stream=True, timeout=timeout_s)
    r.raise_for_status()
    chat_id = None
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
        "content": content,
        "thought_duration": thought_duration,
        "errors": errors,
    }


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


if __name__ == "__main__":
    unittest.main()

