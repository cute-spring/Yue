import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import RunContext

from app.mcp.builtin.docs import DocsListTool, DocsReadTool, DocsReadPdfTool
from app.services.config_service import ConfigService


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=RunContext)
    ctx.deps = {"citations": []}
    return ctx


@pytest.mark.asyncio
async def test_docs_list_returns_structured_error_when_root_dir_invalid(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        os.makedirs(docs_root, exist_ok=True)
        with open(os.path.join(docs_root, "a.txt"), "w", encoding="utf-8") as f:
            f.write("hello")

        with patch("app.mcp.builtin.docs._get_doc_access", return_value=([docs_root], [])):
            tool = DocsListTool()
            resp = await tool.execute(mock_ctx, {"root_dir": "backend/docs", "include_dirs": True})
            payload = json.loads(resp)
            assert payload["ok"] is False
            assert payload["error_code"] == "invalid_root_dir"
            assert payload["requested_root_dir"] == "backend/docs"


@pytest.mark.asyncio
async def test_docs_read_returns_structured_error_when_root_dir_invalid(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        docs_root = os.path.join(tmp, "docs")
        os.makedirs(docs_root, exist_ok=True)
        with open(os.path.join(docs_root, "note.txt"), "w", encoding="utf-8") as f:
            f.write("line1\nline2\nline3\n")

        with patch("app.mcp.builtin.docs._get_doc_access", return_value=([docs_root], [])):
            tool = DocsReadTool()
            resp = await tool.execute(mock_ctx, {"path": "note.txt", "root_dir": "backend/docs"})
            payload = json.loads(resp)
            assert payload["ok"] is False
            assert payload["error_code"] == "invalid_root_dir"


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


@pytest.mark.asyncio
async def test_docs_list_reads_doc_access_each_call_for_immediate_effect(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        root_a = os.path.join(tmp, "a")
        root_b = os.path.join(tmp, "b")
        os.makedirs(root_a, exist_ok=True)
        os.makedirs(root_b, exist_ok=True)
        with open(os.path.join(root_a, "a.txt"), "w", encoding="utf-8") as f:
            f.write("a")
        with open(os.path.join(root_b, "b.txt"), "w", encoding="utf-8") as f:
            f.write("b")

        tool = DocsListTool()
        with patch("app.mcp.builtin.docs._get_doc_access", side_effect=[([root_a], []), ([root_b], [])]):
            first = json.loads(await tool.execute(mock_ctx, {}))
            second = json.loads(await tool.execute(mock_ctx, {}))

        assert first[0]["root"] == os.path.realpath(root_a)
        assert any(item["path"] == "a.txt" for item in first[0]["items"])
        assert second[0]["root"] == os.path.realpath(root_b)
        assert any(item["path"] == "b.txt" for item in second[0]["items"])


@pytest.mark.asyncio
async def test_docs_list_immediate_effect_via_real_config_service_update(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        root_a = os.path.join(tmp, "a")
        root_b = os.path.join(tmp, "b")
        os.makedirs(root_a, exist_ok=True)
        os.makedirs(root_b, exist_ok=True)
        with open(os.path.join(root_a, "a.txt"), "w", encoding="utf-8") as f:
            f.write("a")
        with open(os.path.join(root_b, "b.txt"), "w", encoding="utf-8") as f:
            f.write("b")

        service = ConfigService(os.path.join(tmp, "global_config.json"))
        service.update_doc_access({"allow_roots": [root_a], "deny_roots": []})

        tool = DocsListTool()
        with patch("app.mcp.builtin.docs.config_service", service):
            first = json.loads(await tool.execute(mock_ctx, {}))
            service.update_doc_access({"allow_roots": [root_b], "deny_roots": []})
            second = json.loads(await tool.execute(mock_ctx, {}))

        assert first[0]["root"] == os.path.realpath(root_a)
        assert any(item["path"] == "a.txt" for item in first[0]["items"])
        assert second[0]["root"] == os.path.realpath(root_b)
        assert any(item["path"] == "b.txt" for item in second[0]["items"])


@pytest.mark.asyncio
async def test_docs_list_fails_closed_when_allow_roots_empty(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        service = ConfigService(os.path.join(tmp, "global_config.json"))
        service.update_doc_access({"allow_roots": [], "deny_roots": []})
        tool = DocsListTool()
        with patch("app.mcp.builtin.docs.config_service", service):
            payload = json.loads(await tool.execute(mock_ctx, {}))
        assert payload["ok"] is False
        assert payload["error_code"] == "invalid_root_dir"


@pytest.mark.asyncio
async def test_docs_list_ignores_agent_doc_roots_and_uses_global_doc_access(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        allowed_root = os.path.join(tmp, "allowed")
        restricted_root = os.path.join(allowed_root, "restricted")
        os.makedirs(restricted_root, exist_ok=True)

        mock_ctx.deps = {
            "citations": [],
            "doc_roots": [restricted_root],
        }

        with patch(
            "app.mcp.builtin.docs._get_doc_access",
            return_value=([allowed_root], [restricted_root]),
        ):
            tool = DocsListTool()
            resp_with_root = await tool.execute(mock_ctx, {"root_dir": restricted_root})
            resp_without_root = await tool.execute(mock_ctx, {})

            payload_with_root = json.loads(resp_with_root)
            payload_without_root = json.loads(resp_without_root)

            assert payload_with_root["ok"] is False
            assert payload_with_root["error_code"] == "invalid_root_dir"
            assert isinstance(payload_without_root, list)


@pytest.mark.asyncio
async def test_docs_read_ignores_agent_doc_roots_and_enforces_global_denied_paths(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        allowed_root = os.path.join(tmp, "allowed")
        restricted_root = os.path.join(allowed_root, "restricted")
        os.makedirs(restricted_root, exist_ok=True)
        with open(os.path.join(restricted_root, "note.txt"), "w", encoding="utf-8") as f:
            f.write("line1")

        mock_ctx.deps = {
            "citations": [],
            "doc_roots": [restricted_root],
        }

        with patch(
            "app.mcp.builtin.docs._get_doc_access",
            return_value=([allowed_root], [restricted_root]),
        ):
            tool = DocsReadTool()
            resp_with_root = await tool.execute(mock_ctx, {"path": "note.txt", "root_dir": restricted_root})
            resp_without_root = await tool.execute(mock_ctx, {"path": "restricted/note.txt"})

            payload_with_root = json.loads(resp_with_root)
            payload_without_root = json.loads(resp_without_root)

            assert payload_with_root["ok"] is False
            assert payload_with_root["error_code"] == "invalid_root_dir"
            assert payload_without_root["ok"] is False
            assert payload_without_root["error_code"] == "invalid_root_dir"


def test_root_dir_schema_contains_examples():
    list_tool = DocsListTool()
    read_pdf_tool = DocsReadPdfTool()
    list_desc = list_tool.parameters["properties"]["root_dir"]["description"]
    read_pdf_desc = read_pdf_tool.parameters["properties"]["root_dir"]["description"]
    assert "Examples" in list_desc
    assert "Omit this field" in list_desc
    assert "Examples" in read_pdf_desc


def test_get_doc_access_uses_config_service_roots_entrypoint():
    with patch("app.mcp.builtin.docs.config_service.get_doc_access_roots", return_value=(["/a"], ["/b"])) as getter:
        with patch("app.mcp.builtin.docs.config_service.get_config", return_value={"doc_access": {"allow_roots": ["/wrong"], "deny_roots": ["/wrong"]}}):
            from app.mcp.builtin.docs import _get_doc_access
            allow_roots, deny_roots = _get_doc_access()
    getter.assert_called_once()
    assert allow_roots == ["/a"]
    assert deny_roots == ["/b"]
