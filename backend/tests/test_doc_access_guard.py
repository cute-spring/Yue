import os
import re
from pathlib import Path


FORBIDDEN_PATTERNS = [
    re.compile(r'get_config\(\)\.get\(\s*["\']doc_access["\']\s*\)'),
    re.compile(r'get_config\(\)\[\s*["\']doc_access["\']\s*\]'),
]


def test_backend_app_disallows_direct_doc_access_reads_via_get_config():
    project_root = Path(__file__).resolve().parents[1]
    app_root = project_root / "app"
    offenders: list[str] = []

    for path in app_root.rglob("*.py"):
        rel = os.path.relpath(path, project_root)
        content = path.read_text(encoding="utf-8")
        for idx, line in enumerate(content.splitlines(), start=1):
            if any(pattern.search(line) for pattern in FORBIDDEN_PATTERNS):
                offenders.append(f"{rel}:{idx}:{line.strip()}")

    assert not offenders, "Direct doc_access reads via get_config are forbidden:\n" + "\n".join(offenders)
