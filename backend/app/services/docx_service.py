"""Read-only DOCX package primitives shared by future MCP tools."""

import logging
import re
import time
from typing import Any, Dict, List, Optional
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError

from . import doc_retrieval


DOCX_EXTENSIONS = [".docx"]
READ_BLOCK_LIMIT = 500
TABLE_LIMIT = 100
TABLE_ROW_CELL_LIMIT = 500
RETRIEVAL_RESULT_LIMIT = 200
SEARCH_DOMAINS = {"body", "headings", "table_cells"}
QUERY_FIELDS = {"kind", "heading_path", "style", "section", "table_id", "text", "limit"}
logger = logging.getLogger(__name__)


class DocxService:
    """Expose a small, safe interface for reading ordered DOCX body blocks."""

    def _resolve_path(
        self,
        path: str,
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> str:
        docs_root = doc_retrieval.resolve_docs_root_for_read(
            path,
            requested_root=root_dir,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
            allowed_extensions=DOCX_EXTENSIONS,
            require_md=False,
        )
        return doc_retrieval.resolve_docs_path(
            path,
            docs_root=docs_root,
            require_md=False,
            allowed_extensions=DOCX_EXTENSIONS,
        )

    def extract_blocks(
        self,
        path: str,
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return body content in document order with stable, local locators."""
        started_at = time.monotonic()
        try:
            abs_path = self._resolve_path(path, root_dir, allow_roots, deny_roots)
        except doc_retrieval.DocAccessError:
            self._log_audit(path, started_at, status="failed", error_code="DOCX_ACCESS_DENIED")
            raise
        try:
            document = Document(abs_path)
        except (BadZipFile, KeyError, OSError, PackageNotFoundError, ValueError, XMLSyntaxError):
            self._log_audit(path, started_at, status="failed", error_code="DOCX_PARSE_FAILED")
            return {
                "ok": False,
                "error_code": "DOCX_PARSE_FAILED",
                "message": "The file is not a readable DOCX package.",
                "fidelity_warnings": [],
            }

        blocks: List[Dict[str, Any]] = []
        fidelity_warnings: List[Dict[str, str]] = []
        heading_path: List[str] = []
        for index, element in enumerate(document.element.body.iterchildren(), start=1):
            if isinstance(element, CT_P):
                block = self._paragraph_block(Paragraph(element, document), index)
                if block["kind"] == "heading":
                    heading_path = heading_path[: block["level"] - 1]
                    heading_path.append(block["text"])
                block["locator"] = self._locator(
                    block["block_id"], block["kind"], index, heading_path
                )
                blocks.append(block)
            elif isinstance(element, CT_Tbl):
                blocks.append(self._table_block(Table(element, document), index, heading_path))
            elif element.tag.rsplit("}", maxsplit=1)[-1] != "sectPr":
                fidelity_warnings.append(
                    {
                        "code": "UNSUPPORTED_BODY_ELEMENT",
                        "element": element.tag.rsplit("}", maxsplit=1)[-1],
                    }
                )

        result = {
            "ok": True,
            "file": path,
            "blocks": blocks,
            "fidelity_warnings": fidelity_warnings,
            "elapsed_ms": round((time.monotonic() - started_at) * 1000, 2),
        }
        self._log_audit(
            path,
            started_at,
            blocks=len(blocks),
            fidelity_warnings=len(fidelity_warnings),
        )
        return result

    def profile(
        self,
        path: str,
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        blocks_result = self.extract_blocks(path, root_dir, allow_roots, deny_roots)
        if not blocks_result["ok"]:
            return blocks_result
        document = Document(self._resolve_path(path, root_dir, allow_roots, deny_roots))
        blocks = blocks_result["blocks"]
        return {
            "ok": True,
            "file": path,
            "metadata": {
                "title": document.core_properties.title or "",
                "author": document.core_properties.author or "",
            },
            "counts": {
                "headings": sum(block["kind"] == "heading" for block in blocks),
                "paragraphs": sum(block["kind"] in {"heading", "paragraph", "list_item"} for block in blocks),
                "tables": sum(block["kind"] == "table" for block in blocks),
                "sections": len(document.sections),
            },
            "heading_outline": [{"text": block["text"], "level": block["level"], "block_id": block["block_id"]} for block in blocks if block["kind"] == "heading"],
            "features": {"has_tables": any(block["kind"] == "table" for block in blocks), "has_fidelity_warnings": bool(blocks_result["fidelity_warnings"])},
            "fidelity_warnings": blocks_result["fidelity_warnings"],
        }

    def read(
        self,
        path: str,
        cursor: int = 0,
        limit: int = 200,
        mode: str = "json",
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        result = self.extract_blocks(path, root_dir, allow_roots, deny_roots)
        if not result["ok"]:
            return result
        start = max(cursor, 0)
        end = min(start + min(max(limit, 1), READ_BLOCK_LIMIT), len(result["blocks"]))
        blocks = result["blocks"][start:end]
        is_truncated = end < len(result["blocks"])
        return {
            "ok": True,
            "file": path,
            "data": self._markdown(blocks) if mode == "markdown" else blocks,
            "is_truncated": is_truncated,
            "next_cursor": end if is_truncated else None,
            "citations": [block["locator"] for block in blocks],
            "fidelity_warnings": result["fidelity_warnings"],
        }

    def extract_tables(
        self,
        path: str,
        table_id: Optional[str] = None,
        table_index: Optional[int] = None,
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        result = self.extract_blocks(path, root_dir, allow_roots, deny_roots)
        if not result["ok"]:
            return result
        tables = [block for block in result["blocks"] if block["kind"] == "table"]
        if table_id:
            tables = [table for table in tables if table["table_id"] == table_id]
        elif table_index is not None:
            tables = tables[table_index - 1:table_index]
        is_truncated = len(tables) > TABLE_LIMIT
        tables = tables[:TABLE_LIMIT]
        bounded_tables = []
        for table in tables:
            bounded_rows = []
            for row in table["rows"]:
                if len(row) > TABLE_ROW_CELL_LIMIT:
                    is_truncated = True
                bounded_rows.append(row[:TABLE_ROW_CELL_LIMIT])
            bounded_tables.append({**table, "rows": bounded_rows})
        return {
            "ok": True,
            "file": path,
            "tables": bounded_tables,
            "is_truncated": is_truncated,
            "fidelity_warnings": result["fidelity_warnings"],
        }

    def search(
        self,
        path: str,
        query: str,
        domains: Optional[List[str]] = None,
        regex: bool = False,
        limit: int = 50,
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search a fixed, visible DOCX content domain with stable citations."""
        result = self.extract_blocks(path, root_dir, allow_roots, deny_roots)
        if not result["ok"]:
            return result
        requested_domains = set(domains or ["body", "headings", "table_cells"])
        unsupported = sorted(requested_domains - SEARCH_DOMAINS)
        if unsupported:
            return {
                "ok": False,
                "error_code": "DOCX_SEARCH_INVALID",
                "message": f"Unsupported search domain: {unsupported[0]}",
            }
        try:
            matcher = re.compile(query if regex else re.escape(query), flags=re.IGNORECASE)
        except re.error as error:
            return {"ok": False, "error_code": "DOCX_SEARCH_INVALID", "message": f"Invalid regex: {error}"}
        if not query:
            return {"ok": False, "error_code": "DOCX_SEARCH_INVALID", "message": "Search query must not be empty."}

        matches: List[Dict[str, Any]] = []
        for text, citation, domain in self._searchable_items(result["blocks"]):
            if domain not in requested_domains:
                continue
            spans = [{"start": match.start(), "end": match.end()} for match in matcher.finditer(text)]
            if not spans:
                continue
            matches.append(
                {
                    "text": text,
                    "snippet": self._snippet(text, spans[0]),
                    "match_spans": spans,
                    "score": 1.0,
                    "citation": citation,
                }
            )
        bounded_limit = min(max(limit, 1), RETRIEVAL_RESULT_LIMIT)
        return {
            "ok": True,
            "file": path,
            "query": query,
            "domains": sorted(requested_domains),
            "matches": matches[:bounded_limit],
            "total_matches": len(matches),
            "is_truncated": len(matches) > bounded_limit,
            "limit": bounded_limit,
            "fidelity_warnings": result["fidelity_warnings"],
        }

    def query(
        self,
        path: str,
        query: Dict[str, Any],
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Apply a deliberately closed, document-native filter grammar."""
        unknown_fields = sorted(set(query) - QUERY_FIELDS)
        if unknown_fields:
            return {"ok": False, "error_code": "DOCX_QUERY_INVALID", "message": f"Unsupported query field: {unknown_fields[0]}"}
        if query.get("kind") not in {None, "heading", "paragraph", "list_item", "table"}:
            return {"ok": False, "error_code": "DOCX_QUERY_INVALID", "message": "Unsupported kind filter."}
        if "heading_path" in query and not isinstance(query["heading_path"], list):
            return {"ok": False, "error_code": "DOCX_QUERY_INVALID", "message": "heading_path must be an array."}
        result = self.extract_blocks(path, root_dir, allow_roots, deny_roots)
        if not result["ok"]:
            return result
        applied_filters = {key: value for key, value in query.items() if key != "limit"}
        rows = []
        document = Document(self._resolve_path(path, root_dir, allow_roots, deny_roots))
        block_sections = self._block_sections(document, result["blocks"])
        for ordinal, block in enumerate(result["blocks"], start=1):
            locator = block["locator"]
            if query.get("kind") and block["kind"] != query["kind"]:
                continue
            if query.get("heading_path") is not None and locator["heading_path"] != query["heading_path"]:
                continue
            if query.get("style") and block.get("style") != query["style"]:
                continue
            if query.get("table_id") and block.get("table_id") != query["table_id"]:
                continue
            if query.get("section") is not None and block_sections[ordinal] != query["section"]:
                continue
            text = self._block_text(block)
            if query.get("text") and str(query["text"]).casefold() not in text.casefold():
                continue
            rows.append({"block_id": block["block_id"], "kind": block["kind"], "text": text, "citation": locator})
        bounded_limit = min(max(int(query.get("limit", 50)), 1), RETRIEVAL_RESULT_LIMIT)
        return {
            "ok": True,
            "file": path,
            "applied_filters": applied_filters,
            "results": rows[:bounded_limit],
            "total_results": len(rows),
            "is_truncated": len(rows) > bounded_limit,
            "limit": bounded_limit,
            "fidelity_warnings": result["fidelity_warnings"],
        }

    def structure(
        self,
        path: str,
        root_dir: Optional[str] = None,
        allow_roots: Optional[List[str]] = None,
        deny_roots: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Describe the hierarchy already represented by the ordered block model."""
        result = self.extract_blocks(path, root_dir, allow_roots, deny_roots)
        if not result["ok"]:
            return result
        document = Document(self._resolve_path(path, root_dir, allow_roots, deny_roots))
        blocks = result["blocks"]
        headings = []
        for position, block in enumerate(blocks):
            if block["kind"] != "heading":
                continue
            end = len(blocks)
            for later_position, later in enumerate(blocks[position + 1:], start=position + 2):
                if later["kind"] == "heading" and later["level"] <= block["level"]:
                    end = later_position - 1
                    break
            headings.append({
                "block_id": block["block_id"], "text": block["text"], "level": block["level"],
                "heading_path": block["locator"]["heading_path"],
                "block_range": {"start": position + 1, "end": end},
            })
        return {
            "ok": True,
            "file": path,
            "headings": headings,
            "sections": self._section_ranges(document, blocks),
            "lists": [{"block_id": block["block_id"], "level": block.get("list_level", 1), "text": block["text"]} for block in blocks if block["kind"] == "list_item"],
            "tables": [{"table_id": block["table_id"], "source_index": block["locator"]["source_index"], "heading_path": block["locator"]["heading_path"]} for block in blocks if block["kind"] == "table"],
            "bookmarks": self._bookmarks(document, blocks),
            "headers_footers": {
                "has_headers": any(section.header.paragraphs and any(p.text for p in section.header.paragraphs) for section in document.sections),
                "has_footers": any(section.footer.paragraphs and any(p.text for p in section.footer.paragraphs) for section in document.sections),
            },
            "fidelity_warnings": result["fidelity_warnings"],
        }

    @staticmethod
    def _log_audit(path: str, started_at: float, status: str = "success", **details: Any) -> None:
        logger.info(
            "[DocxAudit] %s",
            {
                "file": path.rsplit("/", maxsplit=1)[-1],
                "elapsed_ms": round((time.monotonic() - started_at) * 1000, 2),
                "status": status,
                **details,
            },
        )

    @staticmethod
    def _searchable_items(blocks: List[Dict[str, Any]]):
        for block in blocks:
            if block["kind"] == "table":
                for row in block["rows"]:
                    for cell in row:
                        yield cell["text"], cell["locator"], "table_cells"
            elif block["kind"] == "heading":
                yield block["text"], block["locator"], "headings"
            else:
                yield block["text"], block["locator"], "body"

    @staticmethod
    def _block_text(block: Dict[str, Any]) -> str:
        if block["kind"] == "table":
            return "\n".join(cell["text"] for row in block["rows"] for cell in row)
        return block["text"]

    @staticmethod
    def _snippet(text: str, span: Dict[str, int], radius: int = 80) -> str:
        start = max(span["start"] - radius, 0)
        end = min(span["end"] + radius, len(text))
        return text[start:end]

    @staticmethod
    def _bookmarks(document: Any, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        body_elements = list(document.element.body.iterchildren())
        locator_by_source = {block["locator"]["source_index"]: block["locator"] for block in blocks}
        bookmarks = []
        for bookmark in document.element.body.iter(f"{namespace}bookmarkStart"):
            owner = next((ancestor for ancestor in bookmark.iterancestors() if ancestor in body_elements), None)
            item: Dict[str, Any] = {
                "name": bookmark.get(f"{namespace}name", ""),
                "id": bookmark.get(f"{namespace}id", ""),
            }
            if owner is not None:
                item["citation"] = locator_by_source.get(body_elements.index(owner) + 1)
            bookmarks.append(item)
        return bookmarks

    @staticmethod
    def _section_ranges(document: Any, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map OOXML paragraph section breaks to the stable body-block coordinates."""
        block_count = len(blocks)
        if not block_count:
            return [{"index": index, "block_range": {"start": 1, "end": 0}} for index, _ in enumerate(document.sections, start=1)]
        source_to_ordinal = {block["locator"]["source_index"]: ordinal for ordinal, block in enumerate(blocks, start=1)}
        section_ends = []
        for source_index, element in enumerate(document.element.body.iterchildren(), start=1):
            if isinstance(element, CT_P) and element.pPr is not None and element.pPr.sectPr is not None:
                section_ends.append(source_to_ordinal[source_index])
        ranges = []
        start = 1
        for index, end in enumerate(section_ends, start=1):
            ranges.append({"index": index, "block_range": {"start": start, "end": end}})
            start = end + 1
        ranges.append({"index": len(ranges) + 1, "block_range": {"start": start, "end": block_count}})
        return ranges

    @classmethod
    def _block_sections(cls, document: Any, blocks: List[Dict[str, Any]]) -> Dict[int, int]:
        result = {}
        for section in cls._section_ranges(document, blocks):
            for ordinal in range(section["block_range"]["start"], section["block_range"]["end"] + 1):
                result[ordinal] = section["index"]
        return result

    @staticmethod
    def _locator(block_id: str, kind: str, source_index: int, heading_path: List[str]) -> Dict[str, Any]:
        return {
            "block_id": block_id,
            "kind": kind,
            "source_index": source_index,
            "heading_path": list(heading_path),
        }

    @staticmethod
    def _markdown(blocks: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for block in blocks:
            if block["kind"] == "heading":
                lines.append(f"{'#' * block['level']} {block['text']}")
            elif block["kind"] == "table":
                for row in block["rows"]:
                    lines.append("| " + " | ".join(cell["text"] for cell in row) + " |")
            else:
                lines.append(block["text"])
        return "\n\n".join(lines)

    @staticmethod
    def _paragraph_block(paragraph: Paragraph, index: int) -> Dict[str, Any]:
        style_name = paragraph.style.name if paragraph.style is not None else ""
        heading = re.fullmatch(r"Heading\s+(\d+)", style_name, flags=re.IGNORECASE)
        block_id = f"p-{index:04d}"
        if heading:
            kind = "heading"
        elif style_name.lower().startswith("list"):
            kind = "list_item"
        else:
            kind = "paragraph"

        block: Dict[str, Any] = {
            "block_id": block_id,
            "kind": kind,
            "text": paragraph.text,
            "style": style_name,
        }
        if heading:
            block["level"] = int(heading.group(1))
        if kind == "list_item":
            number_properties = getattr(getattr(paragraph._p, "pPr", None), "numPr", None)
            nesting_level = getattr(number_properties, "ilvl", None)
            block["list_level"] = int(nesting_level.val) + 1 if nesting_level is not None and nesting_level.val is not None else 1
        return block

    @staticmethod
    def _table_block(table: Table, index: int, heading_path: List[str]) -> Dict[str, Any]:
        table_id = f"table-{index:04d}"
        rows = []
        cell_positions: Dict[int, List[tuple[int, int]]] = {}
        for row_index, row in enumerate(table.rows, start=1):
            cells = []
            for column_index, cell in enumerate(row.cells, start=1):
                cell_positions.setdefault(id(cell._tc), []).append((row_index, column_index))
                cells.append(
                    {
                        "text": cell.text,
                        "locator": {
                            **DocxService._locator(table_id, "table_cell", index, heading_path),
                            "row": row_index,
                            "column": column_index,
                        },
                    }
                )
            rows.append(cells)
        merged_cells = []
        for positions in cell_positions.values():
            if len(positions) > 1:
                rows_in_merge, columns_in_merge = zip(*positions)
                merged_cells.append(
                    {
                        "start": {"row": min(rows_in_merge), "column": min(columns_in_merge)},
                        "end": {"row": max(rows_in_merge), "column": max(columns_in_merge)},
                    }
                )
        return {
            "block_id": table_id,
            "table_id": table_id,
            "kind": "table",
            "locator": DocxService._locator(table_id, "table", index, heading_path),
            "rows": rows,
            "merged_cells": merged_cells,
        }


docx_service = DocxService()
