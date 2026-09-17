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
