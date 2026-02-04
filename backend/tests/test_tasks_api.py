import unittest
import requests
import json
import time

BASE = "http://127.0.0.1:8003"

from _server import ensure_backend_running

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


def _create_parent_chat() -> str:
    events = _collect_sse(
        f"{BASE}/api/chat/stream",
        {"message": "parent", "provider": "__guard__", "model": "guard"},
        timeout_s=15.0,
    )
    for e in events:
        cid = e.get("chat_id")
        if isinstance(cid, str) and cid:
            return cid
    raise AssertionError("missing chat_id in SSE stream")


class TestTasksApi(unittest.TestCase):
    def test_tasks_run_creates_child_chat_with_parent_id(self):
        parent_chat_id = _create_parent_chat()
        r = requests.post(
            f"{BASE}/api/tasks/run",
            json={
                "parent_chat_id": parent_chat_id,
                "tasks": [
                    {
                        "prompt": "ping",
                        "provider": "__guard__",
                        "model": "guard",
                        "title": "t",
                    }
                ],
            },
            timeout=20.0,
        )
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        self.assertEqual(payload.get("parent_chat_id"), parent_chat_id)
        tasks = payload.get("tasks")
        self.assertIsInstance(tasks, list)
        self.assertEqual(len(tasks), 1)
        t0 = tasks[0]
        self.assertEqual(t0.get("status"), "completed")
        self.assertIn("OK", t0.get("output") or "")
        child_chat_id = t0.get("child_chat_id")
        self.assertIsInstance(child_chat_id, str)
        self.assertTrue(child_chat_id)

        c = requests.get(f"{BASE}/api/chat/{child_chat_id}", timeout=10.0)
        self.assertEqual(c.status_code, 200)
        child = c.json()
        self.assertEqual(child.get("parent_id"), parent_chat_id)

    def test_tasks_run_multiple_tasks_preserves_order_and_parent_id(self):
        parent_chat_id = _create_parent_chat()
        titles = ["t1", "t2", "t3"]
        r = requests.post(
            f"{BASE}/api/tasks/run",
            json={
                "parent_chat_id": parent_chat_id,
                "tasks": [
                    {"title": titles[0], "prompt": "ping", "provider": "__guard__", "model": "guard"},
                    {"title": titles[1], "prompt": "ping", "provider": "__guard__", "model": "guard"},
                    {"title": titles[2], "prompt": "ping", "provider": "__guard__", "model": "guard"},
                ],
            },
            timeout=30.0,
        )
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        tasks = payload.get("tasks") or []
        self.assertEqual(len(tasks), 3)
        self.assertEqual([t.get("title") for t in tasks], titles)
        for t in tasks:
            self.assertEqual(t.get("status"), "completed")
            self.assertIn("OK", t.get("output") or "")
            child_chat_id = t.get("child_chat_id")
            self.assertIsInstance(child_chat_id, str)
            self.assertTrue(child_chat_id)
            c = requests.get(f"{BASE}/api/chat/{child_chat_id}", timeout=10.0)
            self.assertEqual(c.status_code, 200)
            child = c.json()
            self.assertEqual(child.get("parent_id"), parent_chat_id)

    def test_tasks_run_parent_not_found(self):
        r = requests.post(
            f"{BASE}/api/tasks/run",
            json={
                "parent_chat_id": "missing-parent",
                "tasks": [{"prompt": "ping", "provider": "__guard__", "model": "guard"}],
            },
            timeout=10.0,
        )
        self.assertEqual(r.status_code, 404)

    def test_tasks_stream_emits_task_events_and_final_result(self):
        parent_chat_id = _create_parent_chat()
        events = _collect_sse(
            f"{BASE}/api/tasks/stream",
            {
                "parent_chat_id": parent_chat_id,
                "tasks": [{"prompt": "ping", "provider": "__guard__", "model": "guard"}],
            },
            timeout_s=20.0,
        )
        task_events = [e for e in events if e.get("type") == "task_event"]
        self.assertTrue(any(e.get("status") == "started" for e in task_events))
        self.assertTrue(any(e.get("status") == "running" for e in task_events))
        self.assertTrue(any(e.get("status") == "completed" for e in task_events))

        final = [e for e in events if e.get("type") == "task_result"]
        self.assertTrue(final)
        result = final[-1].get("result") or {}
        tasks = result.get("tasks") or []
        self.assertEqual(len(tasks), 1)
        self.assertIn("OK", (tasks[0].get("output") or ""))

    def test_tasks_stream_multiple_tasks_events_and_result_order(self):
        parent_chat_id = _create_parent_chat()
        ids = ["task-a", "task-b", "task-c"]
        titles = ["A", "B", "C"]
        events = _collect_sse(
            f"{BASE}/api/tasks/stream",
            {
                "parent_chat_id": parent_chat_id,
                "tasks": [
                    {"id": ids[0], "title": titles[0], "prompt": "ping", "provider": "__guard__", "model": "guard"},
                    {"id": ids[1], "title": titles[1], "prompt": "ping", "provider": "__guard__", "model": "guard"},
                    {"id": ids[2], "title": titles[2], "prompt": "ping", "provider": "__guard__", "model": "guard"},
                ],
            },
            timeout_s=30.0,
        )

        task_events = [e for e in events if e.get("type") == "task_event"]
        by_task: dict[str, list[dict]] = {}
        for e in task_events:
            tid = e.get("task_id")
            if isinstance(tid, str) and tid:
                by_task.setdefault(tid, []).append(e)

        for tid in ids:
            self.assertIn(tid, by_task)
            statuses = {e.get("status") for e in by_task[tid]}
            self.assertIn("started", statuses)
            self.assertIn("running", statuses)
            self.assertIn("completed", statuses)

        final = [e for e in events if e.get("type") == "task_result"]
        self.assertTrue(final)
        result = final[-1].get("result") or {}
        tasks = result.get("tasks") or []
        self.assertEqual(len(tasks), 3)
        self.assertEqual([t.get("task_id") for t in tasks], ids)
        self.assertEqual([t.get("title") for t in tasks], titles)
        for t in tasks:
            self.assertEqual(t.get("status"), "completed")
            self.assertIn("OK", (t.get("output") or ""))

    def test_tasks_stream_parent_not_found_emits_error(self):
        events = _collect_sse(
            f"{BASE}/api/tasks/stream",
            {
                "parent_chat_id": "missing-parent",
                "tasks": [{"prompt": "ping", "provider": "__guard__", "model": "guard"}],
            },
            timeout_s=10.0,
        )
        errors = [e for e in events if e.get("type") == "task_error"]
        self.assertTrue(errors)
        self.assertEqual(errors[-1].get("error"), "parent_chat_not_found")

    def test_tasks_cancel_stops_running_task(self):
        parent_chat_id = _create_parent_chat()

        task_id = "cancel-me"
        payload = {
            "parent_chat_id": parent_chat_id,
            "tasks": [{"id": task_id, "prompt": "slow", "provider": "__slow__", "model": "slow"}],
        }

        with requests.post(f"{BASE}/api/tasks/stream", json=payload, stream=True, timeout=30.0) as r:
            r.raise_for_status()
            cancelled = False
            saw_failed = False
            result_payload = None

            for raw in r.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                if not isinstance(data, dict):
                    continue

                if data.get("type") == "task_event" and data.get("task_id") == task_id:
                    if data.get("status") == "started" and not cancelled:
                        resp = requests.post(
                            f"{BASE}/api/tasks/cancel",
                            json={"parent_chat_id": parent_chat_id, "task_id": task_id},
                            timeout=10.0,
                        )
                        self.assertEqual(resp.status_code, 200)
                        self.assertTrue(resp.json().get("ok"))
                        cancelled = True

                    if data.get("status") == "failed" and data.get("error") == "cancelled":
                        saw_failed = True

                if data.get("type") == "task_result":
                    result_payload = data.get("result") or {}
                    break

            self.assertTrue(cancelled)
            self.assertTrue(saw_failed)
            self.assertIsInstance(result_payload, dict)
            tasks = result_payload.get("tasks") or []
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].get("task_id"), task_id)
            self.assertEqual(tasks[0].get("status"), "failed")
            self.assertEqual(tasks[0].get("error"), "cancelled")

    def test_tasks_stream_deadline_exceeded(self):
        parent_chat_id = _create_parent_chat()

        task_id = "deadline-task"
        deadline_ts = time.time() + 0.05
        payload = {
            "parent_chat_id": parent_chat_id,
            "tasks": [{"id": task_id, "prompt": "slow", "provider": "__slow__", "model": "slow", "deadline_ts": deadline_ts}],
        }

        events = _collect_sse(f"{BASE}/api/tasks/stream", payload, timeout_s=10.0)
        task_events = [e for e in events if e.get("type") == "task_event" and e.get("task_id") == task_id]
        self.assertTrue(task_events)
        self.assertTrue(any(e.get("status") == "failed" and e.get("error") == "deadline_exceeded" for e in task_events))

        final = [e for e in events if e.get("type") == "task_result"]
        self.assertTrue(final)
        result = final[-1].get("result") or {}
        tasks = result.get("tasks") or []
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].get("task_id"), task_id)
        self.assertEqual(tasks[0].get("status"), "failed")
        self.assertEqual(tasks[0].get("error"), "deadline_exceeded")


if __name__ == "__main__":
    unittest.main()
