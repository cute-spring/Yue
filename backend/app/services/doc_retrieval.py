import os
import re
import time
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class DocSnippet:
    path: str
    snippet: str
    score: float
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    start_page: Optional[int] = None
    end_page: Optional[int] = None


class DocAccessError(RuntimeError):
    pass


TEXT_LIKE_EXTENSIONS: List[str] = [
    ".md",
    ".txt",
    ".log",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".html",
]
PDF_EXTENSIONS: List[str] = [".pdf"]


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
    allowed_extensions: Optional[List[str]] = None,
    require_md: bool = True,
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
            candidate = resolve_docs_path(
                requested_path,
                docs_root=root,
                require_md=require_md,
                allowed_extensions=allowed_extensions,
            )
            if not os.path.exists(candidate):
                continue
            return root
        except DocAccessError:
            continue
    raise DocAccessError("Path is outside allowed docs roots")


def resolve_docs_path(
    requested_path: str,
    *,
    docs_root: Optional[str] = None,
    require_md: bool = True,
    allowed_extensions: Optional[List[str]] = None,
    file_patterns: Optional[List[str]] = None,
) -> str:
    docs_root = docs_root or get_docs_root()
    if os.path.isabs(requested_path):
        candidate = requested_path
    else:
        candidate = os.path.join(docs_root, requested_path)
    if not _is_under(docs_root, candidate):
        raise DocAccessError("Path is outside docs root")
    candidate_lower = candidate.lower()
    if allowed_extensions is not None:
        normalized = []
        for ext in allowed_extensions:
            if not isinstance(ext, str):
                continue
            e = ext.strip().lower()
            if not e:
                continue
            if not e.startswith("."):
                e = f".{e}"
            normalized.append(e)
        if not normalized:
            raise DocAccessError("No allowed extensions configured")
        if not any(candidate_lower.endswith(ext) for ext in normalized):
            raise DocAccessError("File extension is not allowed")
    elif require_md and not candidate_lower.endswith(".md"):
        raise DocAccessError("Only .md files are allowed")
    abs_path = _realpath(candidate)
    if file_patterns:
        if not _matches_file_patterns(docs_root, abs_path, file_patterns):
            raise DocAccessError("Path is not allowed by file patterns")
    return abs_path


def _normalize_file_patterns(patterns: List[str]) -> tuple[list[str], list[str]]:
    includes: list[str] = []
    excludes: list[str] = []
    for raw in patterns:
        if not isinstance(raw, str):
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            pat = line[1:].strip()
            if pat:
                excludes.append(pat)
            continue
        includes.append(line)
    return includes, excludes


def _matches_one_pattern(rel_posix: str, pattern: str) -> bool:
    pat = (pattern or "").strip()
    if not pat:
        return False
    rel = PurePosixPath(rel_posix)
    if "/" not in pat:
        return rel.match(pat) or rel.match(f"**/{pat}")
    return rel.match(pat)


def _matches_file_patterns(docs_root: str, abs_path: str, patterns: List[str]) -> bool:
    docs_root_real = _realpath(docs_root)
    abs_real = _realpath(abs_path)
    try:
        rel = os.path.relpath(abs_real, docs_root_real)
    except Exception:
        return False
    rel_posix = rel.replace(os.sep, "/")
    includes, excludes = _normalize_file_patterns(patterns)
    if excludes and any(_matches_one_pattern(rel_posix, p) for p in excludes):
        return False
    if not includes:
        return True
    return any(_matches_one_pattern(rel_posix, p) for p in includes)


def iter_files(
    *,
    docs_root: Optional[str] = None,
    allowed_extensions: Optional[List[str]] = None,
    file_patterns: Optional[List[str]] = None,
    max_files: int = 5000,
) -> Iterable[str]:
    docs_root = docs_root or get_docs_root()
    normalized_exts = None
    if allowed_extensions is not None:
        exts = []
        for ext in allowed_extensions:
            if not isinstance(ext, str):
                continue
            e = ext.strip().lower()
            if not e:
                continue
            if not e.startswith("."):
                e = f".{e}"
            exts.append(e)
        normalized_exts = set(exts)
    count = 0
    for root, _dirs, files in os.walk(docs_root):
        for name in files:
            if normalized_exts is not None:
                if not any(name.lower().endswith(ext) for ext in normalized_exts):
                    continue
            path = os.path.join(root, name)
            if not _is_under(docs_root, path):
                continue
            abs_path = _realpath(path)
            if file_patterns and not _matches_file_patterns(docs_root, abs_path, file_patterns):
                continue
            yield abs_path
            count += 1
            if count >= max_files:
                return


def iter_markdown_files(
    *,
    docs_root: Optional[str] = None,
    max_files: int = 5000,
) -> Iterable[str]:
    return iter_files(docs_root=docs_root, allowed_extensions=[".md"], max_files=max_files)


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
    return read_text_lines(
        requested_path,
        docs_root=docs_root,
        allowed_extensions=[".md"],
        start_line=start_line,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def read_text_lines(
    requested_path: str,
    *,
    docs_root: Optional[str] = None,
    allowed_extensions: Optional[List[str]] = None,
    file_patterns: Optional[List[str]] = None,
    start_line: int = 1,
    max_lines: int = 200,
    max_bytes: int = 2 * 1024 * 1024,
) -> tuple[str, int, int, str]:
    if start_line < 1:
        raise DocAccessError("start_line must be >= 1")
    if max_lines < 1:
        raise DocAccessError("max_lines must be >= 1")
    docs_root = docs_root or get_docs_root()
    abs_path = resolve_docs_path(
        requested_path,
        docs_root=docs_root,
        require_md=False,
        allowed_extensions=allowed_extensions,
        file_patterns=file_patterns,
    )
    text = _read_text_file(abs_path, max_bytes=max_bytes)
    lines = text.splitlines()
    start_idx = start_line - 1
    end_idx = min(start_idx + max_lines, len(lines))
    selected = lines[start_idx:end_idx]
    snippet = "\n".join(selected)
    return abs_path, start_line, max(start_line, end_idx), snippet


def _read_pdf_pages_text(
    path: str,
    *,
    start_page: int,
    max_pages: int,
    max_bytes: int,
    timeout_s: float,
) -> tuple[int, int, str]:
    if start_page < 1:
        raise DocAccessError("start_page must be >= 1")
    if max_pages < 1:
        raise DocAccessError("max_pages must be >= 1")
    st = os.stat(path)
    if st.st_size > max_bytes:
        raise DocAccessError("File too large")
    deadline = time.time() + timeout_s

    from pypdf import PdfReader

    reader = PdfReader(path)
    total_pages = len(reader.pages)
    start_idx = min(max(0, start_page - 1), max(0, total_pages - 1)) if total_pages else 0
    end_idx = min(start_idx + max_pages, total_pages)
    out: List[str] = []
    for i in range(start_idx, end_idx):
        if time.time() > deadline:
            break
        page = reader.pages[i]
        text = page.extract_text() or ""
        out.append(f"[Page {i + 1}]\n{text}".strip())
    rendered = "\n\n".join(out).strip()
    end_page = start_idx + len(out)
    return start_idx + 1, max(start_idx + 1, end_page), rendered


def read_pdf_pages(
    requested_path: str,
    *,
    docs_root: Optional[str] = None,
    file_patterns: Optional[List[str]] = None,
    start_page: int = 1,
    max_pages: int = 3,
    max_bytes: int = 10 * 1024 * 1024,
    timeout_s: float = 3.0,
) -> tuple[str, int, int, str]:
    docs_root = docs_root or get_docs_root()
    abs_path = resolve_docs_path(
        requested_path,
        docs_root=docs_root,
        require_md=False,
        allowed_extensions=PDF_EXTENSIONS,
        file_patterns=file_patterns,
    )
    start, end, snippet = _read_pdf_pages_text(
        abs_path,
        start_page=start_page,
        max_pages=max_pages,
        max_bytes=max_bytes,
        timeout_s=timeout_s,
    )
    return abs_path, start, end, snippet


def _make_snippet(text: str, idx: int, *, window: int = 160) -> str:
    if idx < 0:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    return text[start:end].strip()


def _make_line_snippet(text: str, idx: int, *, window_lines: int = 3, max_lines: int = 20) -> tuple[str, int, int]:
    lines = text.splitlines()
    if not lines:
        return "", 1, 1
    if idx < 0:
        end = min(len(lines), max_lines)
        snippet = "\n".join(lines[0:end])
        return snippet, 1, max(1, end)
    line_idx = text[:idx].count("\n")
    start_idx = max(0, line_idx - window_lines)
    end_idx = min(len(lines), line_idx + window_lines + 1)
    snippet = "\n".join(lines[start_idx:end_idx])
    return snippet, start_idx + 1, max(start_idx + 1, end_idx)


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
    return search_text(
        query,
        docs_root=docs_root,
        allowed_extensions=[".md"],
        limit=limit,
        max_file_bytes=max_file_bytes,
        max_files=max_files,
        timeout_s=timeout_s,
    )


def search_text(
    query: str,
    *,
    docs_root: Optional[str] = None,
    allowed_extensions: Optional[List[str]] = None,
    file_patterns: Optional[List[str]] = None,
    limit: int = 5,
    max_file_bytes: int = 2 * 1024 * 1024,
    max_total_bytes_scanned: int = 10 * 1024 * 1024,
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
    scanned_bytes = 0

    for path in iter_files(
        docs_root=docs_root,
        allowed_extensions=allowed_extensions,
        file_patterns=file_patterns,
        max_files=max_files,
    ):
        if time.time() > deadline:
            break
        try:
            st = os.stat(path)
            if st.st_size > max_file_bytes:
                continue
            if max_total_bytes_scanned > 0 and scanned_bytes + st.st_size > max_total_bytes_scanned:
                break
            scanned_bytes += st.st_size
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
            snippet, start_line, end_line = _make_line_snippet(text, best_idx if best_idx is not None else -1)
            if score <= 0.0:
                continue
            hits.append(DocSnippet(path=path, snippet=snippet, score=score, start_line=start_line, end_line=end_line))
        except Exception:
            continue

    hits.sort(key=lambda h: (-h.score, h.path))
    return hits[: max(0, limit)]


def search_pdf(
    query: str,
    *,
    docs_root: Optional[str] = None,
    file_patterns: Optional[List[str]] = None,
    limit: int = 5,
    max_file_bytes: int = 10 * 1024 * 1024,
    max_total_bytes_scanned: int = 50 * 1024 * 1024,
    max_files: int = 2000,
    max_pages_per_file: int = 6,
    timeout_s: float = 6.0,
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
    scanned_bytes = 0

    for path in iter_files(
        docs_root=docs_root,
        allowed_extensions=PDF_EXTENSIONS,
        file_patterns=file_patterns,
        max_files=max_files,
    ):
        if time.time() > deadline:
            break
        try:
            st = os.stat(path)
            if st.st_size > max_file_bytes:
                continue
            if max_total_bytes_scanned > 0 and scanned_bytes + st.st_size > max_total_bytes_scanned:
                break
            scanned_bytes += st.st_size

            from pypdf import PdfReader

            reader = PdfReader(path)
            total_pages = len(reader.pages)
            pages_to_scan = min(total_pages, max_pages_per_file)
            base = os.path.basename(path).lower()
            score = 0.0
            best_page = None
            best_text = ""
            for t in tokens:
                if t in base:
                    score += 2.0 if len(t) >= 3 else 1.0

            for i in range(pages_to_scan):
                if time.time() > deadline:
                    break
                page = reader.pages[i]
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                lower = text.lower()
                page_score = 0.0
                for t in tokens:
                    if t in lower:
                        page_score += 1.0 if len(t) >= 3 else 0.5
                if page_score <= 0.0:
                    continue
                if best_page is None or page_score > 0.0:
                    best_page = i + 1
                    best_text = text
                    score += page_score
                    break

            if score <= 0.0:
                continue

            if best_page is None:
                snippet = ""
                hits.append(DocSnippet(path=path, snippet=snippet, score=score))
                continue

            lower = best_text.lower()
            idx = -1
            for t in tokens:
                found = lower.find(t)
                if found != -1 and (idx == -1 or found < idx):
                    idx = found
            snippet, start_line, end_line = _make_line_snippet(best_text, idx)
            hits.append(
                DocSnippet(
                    path=path,
                    snippet=snippet,
                    score=score,
                    start_line=start_line,
                    end_line=end_line,
                    start_page=best_page,
                    end_page=best_page,
                )
            )
        except Exception:
            continue

    hits.sort(key=lambda h: (-h.score, h.path))
    return hits[: max(0, limit)]
