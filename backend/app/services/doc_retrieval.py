import os
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class DocSnippet:
    path: str
    snippet: str
    score: float


class DocAccessError(RuntimeError):
    pass


def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))


def get_docs_root() -> str:
    return os.path.join(get_project_root(), "docs")


def resolve_target_root(
    requested_root: str,
    *,
    project_root: Optional[str] = None,
    allow_roots: Optional[List[str]] = None,
) -> str:
    project_root = project_root or get_project_root()
    root = (requested_root or "").strip()
    if not root:
        raise DocAccessError("root is required")
    if os.path.isabs(root):
        candidate = root
    else:
        candidate = os.path.join(project_root, root)
    candidate_real = _realpath(candidate)
    allowed = _is_under(project_root, candidate_real)
    if not allowed and allow_roots:
        for r in allow_roots:
            if not r:
                continue
            r_real = _realpath(r)
            if _is_under(r_real, candidate_real):
                allowed = True
                break
    if not allowed:
        raise DocAccessError("root is not allowed")
    if not os.path.isdir(candidate_real):
        raise DocAccessError("root is not a directory")
    return candidate_real


def _realpath(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def _is_under(root: str, path: str) -> bool:
    root_real = _realpath(root)
    path_real = _realpath(path)
    try:
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        return False


def resolve_docs_path(
    requested_path: str,
    *,
    docs_root: Optional[str] = None,
    require_md: bool = True,
) -> str:
    docs_root = docs_root or get_docs_root()
    if os.path.isabs(requested_path):
        candidate = requested_path
    else:
        candidate = os.path.join(docs_root, requested_path)
    if not _is_under(docs_root, candidate):
        raise DocAccessError("Path is outside docs root")
    if require_md and not candidate.lower().endswith(".md"):
        raise DocAccessError("Only .md files are allowed")
    return _realpath(candidate)


def iter_markdown_files(
    *,
    docs_root: Optional[str] = None,
    max_files: int = 5000,
) -> Iterable[str]:
    docs_root = docs_root or get_docs_root()
    count = 0
    for root, _dirs, files in os.walk(docs_root):
        for name in files:
            if not name.lower().endswith(".md"):
                continue
            path = os.path.join(root, name)
            if not _is_under(docs_root, path):
                continue
            yield _realpath(path)
            count += 1
            if count >= max_files:
                return


def _read_text_file(path: str, *, max_bytes: int) -> str:
    st = os.stat(path)
    if st.st_size > max_bytes:
        raise DocAccessError("File too large")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_markdown_lines(
    requested_path: str,
    *,
    docs_root: Optional[str] = None,
    start_line: int = 1,
    max_lines: int = 200,
    max_bytes: int = 2 * 1024 * 1024,
) -> tuple[str, int, int, str]:
    if start_line < 1:
        raise DocAccessError("start_line must be >= 1")
    if max_lines < 1:
        raise DocAccessError("max_lines must be >= 1")
    docs_root = docs_root or get_docs_root()
    abs_path = resolve_docs_path(requested_path, docs_root=docs_root, require_md=True)
    text = _read_text_file(abs_path, max_bytes=max_bytes)
    lines = text.splitlines()
    start_idx = start_line - 1
    end_idx = min(start_idx + max_lines, len(lines))
    selected = lines[start_idx:end_idx]
    snippet = "\n".join(selected)
    return abs_path, start_line, max(start_line, end_idx), snippet


def _make_snippet(text: str, idx: int, *, window: int = 160) -> str:
    if idx < 0:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    return text[start:end].strip()


def _tokenize_query(query: str) -> List[str]:
    q = (query or "").strip().lower()
    if not q:
        return []
    parts = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", q)
    tokens: List[str] = []
    for p in parts:
        if not p:
            continue
        if re.fullmatch(r"[a-z0-9]+", p):
            if len(p) >= 2:
                tokens.append(p)
            continue
        if len(p) >= 2:
            tokens.append(p)
        if len(p) > 2:
            tokens.extend(p[i : i + 2] for i in range(len(p) - 1))
    seen = set()
    out: List[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def search_markdown(
    query: str,
    *,
    docs_root: Optional[str] = None,
    limit: int = 5,
    max_file_bytes: int = 2 * 1024 * 1024,
    max_files: int = 5000,
    timeout_s: float = 2.0,
) -> List[DocSnippet]:
    q = (query or "").strip()
    if not q:
        return []
    tokens = _tokenize_query(q)
    if not tokens:
        return []
    docs_root = docs_root or get_docs_root()
    deadline = time.time() + timeout_s
    hits: List[DocSnippet] = []

    for path in iter_markdown_files(docs_root=docs_root, max_files=max_files):
        if time.time() > deadline:
            break
        try:
            st = os.stat(path)
            if st.st_size > max_file_bytes:
                continue
            base = os.path.basename(path).lower()
            score = 0.0
            text = _read_text_file(path, max_bytes=max_file_bytes)
            lower = text.lower()
            best_idx = None
            for t in tokens:
                if t in base:
                    score += 2.0 if len(t) >= 3 else 1.0
                idx = lower.find(t)
                if idx != -1:
                    score += 1.0 if len(t) >= 3 else 0.5
                    if best_idx is None or idx < best_idx:
                        best_idx = idx
            snippet = _make_snippet(text, best_idx if best_idx is not None else -1)
            if score <= 0.0:
                continue
            hits.append(DocSnippet(path=path, snippet=snippet, score=score))
        except Exception:
            continue

    hits.sort(key=lambda h: (-h.score, h.path))
    return hits[: max(0, limit)]
