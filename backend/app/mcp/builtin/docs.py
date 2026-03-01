from typing import Any, Dict, List, Optional
import json
import logging
from pydantic_ai import RunContext

from app.services import doc_retrieval
from app.services.config_service import config_service
from ..base import BaseTool
from .registry import builtin_tool_registry

logger = logging.getLogger(__name__)

def _get_doc_access() -> tuple[List[str], List[str]]:
    cfg = config_service.get_config().get("doc_access", {})
    allow_roots = cfg.get("allow_roots") if isinstance(cfg, dict) else None
    deny_roots = cfg.get("deny_roots") if isinstance(cfg, dict) else None
    return allow_roots or [], deny_roots or []

class DocsListTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="docs_list",
            description="List files and directories under Yue/docs (or root_dir). Returns a tree-like listing with paths relative to the docs root.",
            parameters={
                "type": "object",
                "properties": {
                    "root_dir": {"type": "string"},
                    "max_items": {"type": "integer"},
                    "max_depth": {"type": "integer"},
                    "include_dirs": {"type": "boolean"},
                },
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        root_dir = args.get("root_dir")
        max_items = args.get("max_items", 2000)
        max_depth = args.get("max_depth", 6)
        include_dirs = args.get("include_dirs", True)

        allow_roots, deny_roots = _get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        roots = doc_retrieval.resolve_docs_roots_for_search(
            root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )
        remaining = max(0, max_items)
        payload = []
        for docs_root in roots:
            if remaining <= 0:
                break
            items = doc_retrieval.list_docs_tree(
                docs_root=docs_root,
                file_patterns=file_patterns if isinstance(file_patterns, list) else None,
                max_items=remaining,
                max_depth=max_depth,
                include_dirs=include_dirs,
            )
            payload.append({"root": docs_root, "items": items})
            remaining -= len(items)
        return json.dumps(payload, ensure_ascii=False, indent=2)

class DocsSearchTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="docs_search",
            description="Fast keyword search under Yue/docs (or root_dir) using Ripgrep. Returns smart snippets with line numbers. Use concise keywords (2-3 words) for best performance. mode=markdown/text.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "mode": {"type": "string"},
                    "root_dir": {"type": "string"},
                    "limit": {"type": "integer", "description": "Maximum number of files to return."},
                    "max_files": {"type": "integer"},
                    "timeout_s": {"type": "number"},
                },
                "required": ["query"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        query = args.get("query")
        mode = args.get("mode", "text")
        root_dir = args.get("root_dir")
        limit = args.get("limit", 5)
        max_files = args.get("max_files", 5000)
        timeout_s = args.get("timeout_s", 2.0)
        
        if timeout_s is None:
            timeout_s = 2.0
        
        normalized_mode = (mode or "text").strip().lower()
        if normalized_mode == "markdown":
            allowed_extensions = [".md"]
        else:
            allowed_extensions = doc_retrieval.TEXT_LIKE_EXTENSIONS

        allow_roots, deny_roots = _get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        roots = doc_retrieval.resolve_docs_roots_for_search(
            root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )

        merged = {}
        for docs_root in roots:
            hits = doc_retrieval.search_text(
                query,
                docs_root=docs_root,
                allowed_extensions=allowed_extensions,
                file_patterns=file_patterns if isinstance(file_patterns, list) else None,
                limit=limit,
                max_files=max_files,
                timeout_s=timeout_s,
            )
            for h in hits:
                existing = merged.get(h.path)
                if not existing or h.score > existing.score:
                    merged[h.path] = h
        hits = sorted(merged.values(), key=lambda h: (-h.score, h.path))[: max(0, limit)]

        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                existing = {c.get("path") for c in citations if isinstance(c, dict)}
                for h in hits:
                    if h.path in existing:
                        continue
                    entry = {"path": h.path, "snippet": h.snippet, "score": h.score}
                    if getattr(h, "start_line", None) is not None:
                        entry["start_line"] = h.start_line
                    if getattr(h, "end_line", None) is not None:
                        entry["end_line"] = h.end_line
                    citations.append(entry)
                    existing.add(h.path)

        payload = []
        for h in hits:
            item = {"path": h.path, "snippet": h.snippet, "score": h.score}
            if getattr(h, "start_line", None) is not None:
                item["start_line"] = h.start_line
            if getattr(h, "end_line", None) is not None:
                item["end_line"] = h.end_line
            payload.append(item)
        return json.dumps(payload, ensure_ascii=False, indent=2)

class DocsReadTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="docs_read",
            description="Read file content. Only use this if `docs_search` snippets are insufficient. Supports pagination or centering via `target_line`.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "mode": {"type": "string"},
                    "root_dir": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "max_lines": {"type": "integer"},
                    "target_line": {"type": "integer"},
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        mode = args.get("mode", "text")
        root_dir = args.get("root_dir")
        start_line = args.get("start_line")
        max_lines = args.get("max_lines", 200)
        target_line = args.get("target_line")

        normalized_mode = (mode or "text").strip().lower()
        if normalized_mode == "markdown":
            if path and not path.lower().endswith(".md"):
                allowed_extensions = doc_retrieval.TEXT_LIKE_EXTENSIONS
            else:
                allowed_extensions = [".md"]
        else:
            allowed_extensions = doc_retrieval.TEXT_LIKE_EXTENSIONS

        allow_roots, deny_roots = _get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None

        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=allowed_extensions,
            require_md=False,
        )
        abs_path, start, end, snippet = doc_retrieval.read_text_lines(
            path,
            docs_root=docs_root,
            allowed_extensions=allowed_extensions,
            file_patterns=file_patterns if isinstance(file_patterns, list) else None,
            start_line=start_line,
            max_lines=max_lines,
            target_line=target_line,
        )
        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                citations.append(
                    {
                        "path": abs_path,
                        "start_line": start,
                        "end_line": end,
                        "snippet": snippet,
                    }
                )
        return f"{abs_path}#L{start}-L{end}\n{snippet}"

class DocsInspectTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="docs_inspect",
            description="Inspect document metadata and structure.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "root_dir": {"type": "string"},
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        root_dir = args.get("root_dir")

        allow_roots, deny_roots = _get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        
        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=doc_retrieval.TEXT_LIKE_EXTENSIONS,
            require_md=False,
        )
        
        info = doc_retrieval.inspect_doc(
            path,
            docs_root=docs_root,
            allowed_extensions=doc_retrieval.TEXT_LIKE_EXTENSIONS,
        )
        return json.dumps(info, ensure_ascii=False, indent=2)

class DocsSearchPdfTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="docs_search_pdf",
            description="Search within PDF documents.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "root_dir": {"type": "string"},
                    "limit": {"type": "integer"},
                    "max_files": {"type": "integer"},
                    "timeout_s": {"type": "number"},
                    "max_pages_per_file": {"type": "integer"},
                },
                "required": ["query"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        query = args.get("query")
        root_dir = args.get("root_dir")
        limit = args.get("limit", 5)
        max_files = args.get("max_files", 2000)
        timeout_s = args.get("timeout_s", 6.0)
        max_pages_per_file = args.get("max_pages_per_file", 6)

        if timeout_s is None:
            timeout_s = 6.0
            
        allow_roots, deny_roots = _get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        roots = doc_retrieval.resolve_docs_roots_for_search(
            root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )

        merged = {}
        for docs_root in roots:
            hits = doc_retrieval.search_pdf(
                query,
                docs_root=docs_root,
                file_patterns=file_patterns if isinstance(file_patterns, list) else None,
                limit=limit,
                max_files=max_files,
                timeout_s=timeout_s,
                max_pages_per_file=max_pages_per_file,
            )
            for h in hits:
                existing = merged.get(h.path)
                if not existing or h.score > existing.score:
                    merged[h.path] = h
        hits = sorted(merged.values(), key=lambda h: (-h.score, h.path))[: max(0, limit)]

        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                existing = {c.get("path") for c in citations if isinstance(c, dict)}
                for h in hits:
                    if h.path in existing:
                        continue
                    entry = {"path": h.path, "snippet": h.snippet, "score": h.score}
                    if getattr(h, "start_page", None) is not None:
                        entry["start_page"] = h.start_page
                    if getattr(h, "end_page", None) is not None:
                        entry["end_page"] = h.end_page
                    citations.append(entry)
                    existing.add(h.path)

        payload = []
        for h in hits:
            item = {"path": h.path, "snippet": h.snippet, "score": h.score}
            if getattr(h, "start_page", None) is not None:
                item["start_page"] = h.start_page
            if getattr(h, "end_page", None) is not None:
                item["end_page"] = h.end_page
            payload.append(item)
        return json.dumps(payload, ensure_ascii=False, indent=2)

class DocsReadPdfTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="docs_read_pdf",
            description="Read content from PDF pages.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "root_dir": {"type": "string"},
                    "start_page": {"type": "integer"},
                    "max_pages": {"type": "integer"},
                    "timeout_s": {"type": "number"},
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        root_dir = args.get("root_dir")
        start_page = args.get("start_page")
        max_pages = args.get("max_pages", 6)
        timeout_s = args.get("timeout_s", 3.0)

        if timeout_s is None:
            timeout_s = 3.0
            
        allow_roots, deny_roots = _get_doc_access()
        deps = getattr(ctx, "deps", None)
        doc_roots = deps.get("doc_roots") if isinstance(deps, dict) else None
        file_patterns = deps.get("doc_file_patterns") if isinstance(deps, dict) else None
        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=doc_retrieval.PDF_EXTENSIONS,
            require_md=False,
        )
        abs_path, start, end, snippet = doc_retrieval.read_pdf_pages(
            path,
            docs_root=docs_root,
            file_patterns=file_patterns if isinstance(file_patterns, list) else None,
            start_page=start_page,
            max_pages=max_pages,
            timeout_s=timeout_s,
        )
        if isinstance(deps, dict):
            citations = deps.get("citations")
            if isinstance(citations, list):
                citations.append(
                    {
                        "path": abs_path,
                        "start_page": start,
                        "end_page": end,
                        "snippet": snippet,
                    }
                )
        return f"{abs_path}#P{start}-P{end}\n{snippet}"

# Register all docs tools
builtin_tool_registry.register(DocsListTool())
builtin_tool_registry.register(DocsSearchTool())
builtin_tool_registry.register(DocsReadTool())
builtin_tool_registry.register(DocsInspectTool())
builtin_tool_registry.register(DocsSearchPdfTool())
builtin_tool_registry.register(DocsReadPdfTool())
