import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import RunContext

from app.mcp.builtin.docs import DocsListTool, DocsReadTool, DocsReadPdfTool


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=RunContext)
    ctx.deps = {"citations": []}
    return ctx


@pytest.mark.asyncio
async def test_docs_list_fallback_to_default_root_when_root_dir_invalid(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        os.makedirs(docs_root, exist_ok=True)
        with open(os.path.join(docs_root, "a.txt"), "w", encoding="utf-8") as f:
            f.write("hello")

        with patch("app.mcp.builtin.docs._get_doc_access", return_value=([docs_root], [])):
            tool = DocsListTool()
            resp = await tool.execute(mock_ctx, {"root_dir": "backend/docs", "include_dirs": True})
            payload = json.loads(resp)
            assert isinstance(payload, list)
            assert payload
            assert payload[0]["root"] == os.path.realpath(docs_root)
            assert any(item["path"] == "a.txt" for item in payload[0]["items"])


@pytest.mark.asyncio
async def test_docs_read_fallback_to_default_root_when_root_dir_invalid(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        os.makedirs(docs_root, exist_ok=True)
        with open(os.path.join(docs_root, "note.txt"), "w", encoding="utf-8") as f:
            f.write("line1\nline2\nline3\n")

        with patch("app.mcp.builtin.docs._get_doc_access", return_value=([docs_root], [])):
            tool = DocsReadTool()
            resp = await tool.execute(mock_ctx, {"path": "note.txt", "root_dir": "backend/docs"})
            assert "#L1-L3" in resp
            assert "line1" in resp


@pytest.mark.asyncio
async def test_docs_read_returns_structured_invalid_root_error(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        os.makedirs(docs_root, exist_ok=True)
        outside_path = os.path.realpath(os.path.join(tmp, "..", "outside.txt"))

        with patch("app.mcp.builtin.docs._get_doc_access", return_value=([docs_root], [])):
            tool = DocsReadTool()
            resp = await tool.execute(
                mock_ctx,
                {"path": outside_path, "root_dir": "backend/docs"},
            )
            payload = json.loads(resp)
            assert payload["ok"] is False
            assert payload["error_code"] == "invalid_root_dir"
            assert "omit root_dir" in payload["hint"]
            assert payload["requested_root_dir"] == "backend/docs"


def test_root_dir_schema_contains_examples():
    list_tool = DocsListTool()
    read_pdf_tool = DocsReadPdfTool()
    list_desc = list_tool.parameters["properties"]["root_dir"]["description"]
    read_pdf_desc = read_pdf_tool.parameters["properties"]["root_dir"]["description"]
    assert "Examples" in list_desc
    assert "Omit this field" in list_desc
    assert "Examples" in read_pdf_desc
