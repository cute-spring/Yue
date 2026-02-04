import json
import time
import unittest

import requests

from _server import ensure_backend_running

BASE = "http://127.0.0.1:8003"

ensure_backend_running(BASE)


class TestSseDisconnect(unittest.TestCase):
    def test_tasks_stream_disconnect_cancels_runner(self):
        parent = requests.post(
            f"{BASE}/api/chat/stream",
            json={"message": "parent", "provider": "__guard__", "model": "guard"},
            stream=True,
            timeout=10.0,
        )
        parent.raise_for_status()
        chat_id = None
        for raw in parent.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            cid = data.get("chat_id")
            if isinstance(cid, str) and cid:
                chat_id = cid
                break
        parent.close()
        self.assertTrue(chat_id)

        task_id = "disconnect-task"
        r = requests.post(
            f"{BASE}/api/tasks/stream",
            json={"parent_chat_id": chat_id, "tasks": [{"id": task_id, "prompt": "slow", "provider": "__slow__", "model": "slow"}]},
            stream=True,
            timeout=10.0,
        )
        r.raise_for_status()

        saw_started = False
        start = time.time()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data.get("type") == "task_event" and data.get("task_id") == task_id and data.get("status") == "started":
                saw_started = True
                break
            if time.time() - start > 5.0:
                break
        r.close()
        self.assertTrue(saw_started)

        deadline = time.time() + 3.0
        while time.time() < deadline:
            c = requests.post(f"{BASE}/api/tasks/cancel", json={"parent_chat_id": chat_id, "task_id": task_id}, timeout=5.0)
            self.assertEqual(c.status_code, 200)
            ok = c.json().get("ok")
            if ok is False:
                return
            time.sleep(0.2)
        raise AssertionError("task still running after client disconnect")


if __name__ == "__main__":
    unittest.main()

