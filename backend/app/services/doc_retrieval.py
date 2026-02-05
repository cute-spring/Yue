import os
import re
import time
import sys
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


def _realpath(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def _is_under(root: str, path: str) -> bool:
    root_real = _realpath(root)
    path_real = _realpath(path)
    try:
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        return False


def _default_deny_roots() -> List[str]:
    if sys.platform.startswith("darwin"):
        return ["/System", "/Library"]
    return ["/etc", "/proc", "/sys", "/dev"]


def resolve_docs_root(
    requested_root: Optional[str],
    *,
    allow_roots: Optional[List[str]] = None,
    deny_roots: Optional[List[str]] = None,
) -> str:
    allow = allow_roots or [get_docs_root()]
    allow = [_realpath(p) for p in allow if isinstance(p, str) and p.strip()]
    deny = _default_deny_roots()
    if deny_roots:
        deny.extend([p for p in deny_roots if isinstance(p, str) and p.strip()])
    deny = [_realpath(p) for p in deny]
    candidate = requested_root or allow[0]
    if not os.path.isabs(candidate):
        candidate = os.path.join(get_project_root(), candidate)
    candidate = _realpath(candidate)
    if not any(_is_under(a, candidate) for a in allow):
        raise DocAccessError("Root is outside allowed docs roots")
    if any(_is_under(d, candidate) for d in deny):
        raise DocAccessError("Root is under denied paths")
    return candidate


def resolve_docs_roots_for_search(
    requested_root: Optional[str],
    *,
    doc_roots: Optional[List[str]] = None,
    allow_roots: Optional[List[str]] = None,
    deny_roots: Optional[List[str]] = None,
) -> List[str]:
    if requested_root:
        return [resolve_docs_root(requested_root, allow_roots=allow_roots, deny_roots=deny_roots)]
    roots = []
    if doc_roots:
        for root in doc_roots:
            if not isinstance(root, str) or not root.strip():
                continue
            try:
                roots.append(resolve_docs_root(root, allow_roots=allow_roots, deny_roots=deny_roots))
            except DocAccessError:
                continue
    if roots:
        return roots
    return [resolve_docs_root(None, allow_roots=allow_roots, deny_roots=deny_roots)]


def resolve_docs_root_for_read(
    requested_path: str,
    *,
    requested_root: Optional[str] = None,
    doc_roots: Optional[List[str]] = None,
    allow_roots: Optional[List[str]] = None,
    deny_roots: Optional[List[str]] = None,
) -> str:
    if requested_root:
        return resolve_docs_root(requested_root, allow_roots=allow_roots, deny_roots=deny_roots)
    roots = resolve_docs_roots_for_search(
        None,
        doc_roots=doc_roots,
        allow_roots=allow_roots,
        deny_roots=deny_roots,
    )
    if os.path.isabs(requested_path):
        for root in roots:
            if _is_under(root, requested_path):
                return root
        raise DocAccessError("Path is outside allowed docs roots")
    if len(roots) == 1:
        return roots[0]
    for root in roots:
        try:
            resolve_docs_path(requested_path, docs_root=root, require_md=True)
            return root
        except DocAccessError:
            continue
    raise DocAccessError("Path is outside allowed docs roots")


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
