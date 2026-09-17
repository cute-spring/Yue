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
