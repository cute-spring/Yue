import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docx import Document
from pydantic_ai import RunContext

from app.mcp.builtin.docx import DocxExtractTablesTool, DocxProfileTool, DocxReadTool
from app.mcp.builtin.registry import builtin_tool_registry


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    path = tmp_path / "brief.docx"
    document = Document()
    document.core_properties.title = "Product brief"
    document.core_properties.author = "Yue"
    document.add_heading("Summary", level=1)
    document.add_paragraph("First paragraph.")
    document.add_paragraph("Second paragraph.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Status"
    table.cell(1, 1).text = "Ready"
    document.save(path)
    return path


@pytest.fixture
def mock_ctx():
    return MagicMock(spec=RunContext)


@pytest.mark.asyncio
async def test_docx_profile_returns_document_summary(mock_ctx, sample_docx):
    with patch("app.mcp.builtin.docx._get_doc_access", return_value=([str(sample_docx.parent)], [])):
        payload = json.loads(
            await DocxProfileTool().execute(mock_ctx, {"path": sample_docx.name, "root_dir": str(sample_docx.parent)})
        )

    assert payload["ok"] is True
    assert payload["tool"] == "docx_profile"
    assert payload["metadata"]["title"] == "Product brief"
    assert payload["counts"] == {"headings": 1, "paragraphs": 3, "tables": 1, "sections": 1}
    assert payload["heading_outline"] == [{"text": "Summary", "level": 1, "block_id": "p-0001"}]
    assert payload["features"]["has_tables"] is True


@pytest.mark.asyncio
async def test_docx_read_paginates_blocks_and_renders_markdown(mock_ctx, sample_docx):
    with patch("app.mcp.builtin.docx._get_doc_access", return_value=([str(sample_docx.parent)], [])):
        payload = json.loads(
            await DocxReadTool().execute(
                mock_ctx,
                {"path": sample_docx.name, "root_dir": str(sample_docx.parent), "limit": 2, "mode": "markdown"},
            )
        )

    assert payload["ok"] is True
    assert payload["tool"] == "docx_read"
    assert payload["is_truncated"] is True
    assert payload["next_cursor"] == 2
    assert "# Summary" in payload["data"]
    assert payload["citations"][0]["block_id"] == "p-0001"


@pytest.mark.asyncio
async def test_docx_extract_tables_selects_a_table_by_id(mock_ctx, sample_docx):
    with patch("app.mcp.builtin.docx._get_doc_access", return_value=([str(sample_docx.parent)], [])):
        payload = json.loads(
            await DocxExtractTablesTool().execute(
                mock_ctx,
                {"path": sample_docx.name, "root_dir": str(sample_docx.parent), "table_index": 1},
            )
        )

    assert payload["ok"] is True
    assert payload["tool"] == "docx_extract_tables"
    assert payload["tables"][0]["table_id"] == "table-0004"
    assert payload["tables"][0]["rows"][1][1]["text"] == "Ready"


@pytest.mark.asyncio
async def test_docx_extract_tables_bounds_large_table_cells(mock_ctx, tmp_path: Path):
    path = tmp_path / "large-table.docx"
    document = Document()
    table = document.add_table(rows=1, cols=501)
    for index, cell in enumerate(table.rows[0].cells):
        cell.text = str(index)
    document.save(path)

    with patch("app.mcp.builtin.docx._get_doc_access", return_value=([str(tmp_path)], [])):
        payload = json.loads(
            await DocxExtractTablesTool().execute(
                mock_ctx,
                {"path": path.name, "root_dir": str(tmp_path)},
            )
        )

    assert payload["ok"] is True
    assert payload["is_truncated"] is True
    assert len(payload["tables"][0]["rows"][0]) == 500


def test_registry_contains_docx_reader_tools():
    names = [tool.name for tool in builtin_tool_registry.get_all_tools()]
    assert {"docx_profile", "docx_read", "docx_extract_tables"}.issubset(names)
