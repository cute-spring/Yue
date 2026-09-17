import json
from typing import Any, Dict, List

from pydantic_ai import RunContext

from app.services.config_service import config_service
from app.services.docx_service import docx_service

from ..base import BaseTool
from .registry import builtin_tool_registry


def _get_doc_access() -> tuple[List[str], List[str]]:
    return config_service.get_doc_access_roots()


class _DocxTool(BaseTool):
    error_code = "DOCX_FAILED"

    async def _execute(self, args: Dict[str, Any]) -> str:
        allow_roots, deny_roots = _get_doc_access()
        try:
            result = self.handler(args, allow_roots, deny_roots)
            result["tool"] = self.name
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as error:
            return json.dumps(
                {"ok": False, "tool": self.name, "error_code": self.error_code, "message": str(error)},
                ensure_ascii=False,
                indent=2,
            )


class DocxProfileTool(_DocxTool):
    error_code = "DOCX_PROFILE_FAILED"

    def __init__(self):
        super().__init__("docx_profile", "Profile a DOCX document before reading it.", {"type": "object", "properties": {"path": {"type": "string"}, "root_dir": {"type": "string"}}, "required": ["path"]})

    def handler(self, args: Dict[str, Any], allow_roots: List[str], deny_roots: List[str]) -> Dict[str, Any]:
        return docx_service.profile(args["path"], args.get("root_dir"), allow_roots, deny_roots)

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self._execute(args)


class DocxReadTool(_DocxTool):
    error_code = "DOCX_READ_FAILED"

    def __init__(self):
        super().__init__("docx_read", "Read bounded DOCX body blocks in JSON or Markdown.", {"type": "object", "properties": {"path": {"type": "string"}, "cursor": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 500}, "mode": {"type": "string", "enum": ["json", "markdown"]}, "root_dir": {"type": "string"}}, "required": ["path"]})

    def handler(self, args: Dict[str, Any], allow_roots: List[str], deny_roots: List[str]) -> Dict[str, Any]:
        return docx_service.read(args["path"], args.get("cursor", 0), args.get("limit", 200), args.get("mode", "json"), args.get("root_dir"), allow_roots, deny_roots)

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self._execute(args)


class DocxExtractTablesTool(_DocxTool):
    error_code = "DOCX_EXTRACT_TABLES_FAILED"

    def __init__(self):
        super().__init__("docx_extract_tables", "Extract DOCX tables with stable table and cell locators.", {"type": "object", "properties": {"path": {"type": "string"}, "table_id": {"type": "string"}, "table_index": {"type": "integer", "minimum": 1}, "root_dir": {"type": "string"}}, "required": ["path"]})

    def handler(self, args: Dict[str, Any], allow_roots: List[str], deny_roots: List[str]) -> Dict[str, Any]:
        return docx_service.extract_tables(args["path"], args.get("table_id"), args.get("table_index"), args.get("root_dir"), allow_roots, deny_roots)

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self._execute(args)


class DocxSearchTool(_DocxTool):
    error_code = "DOCX_SEARCH_FAILED"

    def __init__(self):
        super().__init__(
            "docx_search",
            "Search visible DOCX text and table cells with stable citations.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "query": {"type": "string", "minLength": 1},
                    "domains": {"type": "array", "items": {"type": "string", "enum": ["body", "headings", "table_cells"]}},
                    "regex": {"type": "boolean"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    "root_dir": {"type": "string"},
                },
                "required": ["path", "query"],
            },
        )

    def handler(self, args: Dict[str, Any], allow_roots: List[str], deny_roots: List[str]) -> Dict[str, Any]:
        return docx_service.search(
            args["path"], args["query"], args.get("domains"), args.get("regex", False), args.get("limit", 50),
            args.get("root_dir"), allow_roots, deny_roots,
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self._execute(args)


class DocxQueryTool(_DocxTool):
    error_code = "DOCX_QUERY_FAILED"

    def __init__(self):
        super().__init__(
            "docx_query",
            "Run a constrained, deterministic query over DOCX body blocks.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "query": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": ["heading", "paragraph", "list_item", "table"]},
                            "heading_path": {"type": "array", "items": {"type": "string"}},
                            "style": {"type": "string"}, "section": {"type": "integer", "minimum": 1},
                            "table_id": {"type": "string"}, "text": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                        },
                        "additionalProperties": False,
                    },
                    "root_dir": {"type": "string"},
                },
                "required": ["path", "query"],
            },
        )

    def handler(self, args: Dict[str, Any], allow_roots: List[str], deny_roots: List[str]) -> Dict[str, Any]:
        return docx_service.query(args["path"], args["query"], args.get("root_dir"), allow_roots, deny_roots)

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self._execute(args)


class DocxStructureTool(_DocxTool):
    error_code = "DOCX_STRUCTURE_FAILED"

    def __init__(self):
        super().__init__(
            "docx_structure",
            "Describe DOCX headings, sections, lists, tables, bookmarks, headers, and footers.",
            {"type": "object", "properties": {"path": {"type": "string"}, "root_dir": {"type": "string"}}, "required": ["path"]},
        )

    def handler(self, args: Dict[str, Any], allow_roots: List[str], deny_roots: List[str]) -> Dict[str, Any]:
        return docx_service.structure(args["path"], args.get("root_dir"), allow_roots, deny_roots)

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        return await self._execute(args)


builtin_tool_registry.register(DocxProfileTool())
builtin_tool_registry.register(DocxReadTool())
builtin_tool_registry.register(DocxExtractTablesTool())
builtin_tool_registry.register(DocxSearchTool())
builtin_tool_registry.register(DocxQueryTool())
builtin_tool_registry.register(DocxStructureTool())
