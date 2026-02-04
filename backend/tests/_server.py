import atexit
import os
import subprocess
import sys
import time

import requests


_server_process: subprocess.Popen | None = None


def ensure_backend_running(base_url: str = "http://127.0.0.1:8003", timeout_s: float = 25.0) -> None:
    global _server_process

    if _server_process is not None:
        return

    try:
        r = requests.get(f"{base_url}/api/mcp/status", timeout=0.5)
        if r.ok:
            return
    except Exception:
        pass

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    backend_dir = os.path.join(repo_root, "backend")

    _server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8003",
        ],
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
    )

    def _cleanup() -> None:
        global _server_process
        p = _server_process
        _server_process = None
        if not p:
            return
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    atexit.register(_cleanup)

    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = requests.get(f"{base_url}/api/mcp/status", timeout=0.5)
            if r.ok:
                return
        except Exception:
            time.sleep(0.2)

    raise RuntimeError("backend_not_ready")

