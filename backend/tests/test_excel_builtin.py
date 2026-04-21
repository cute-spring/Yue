import pytest
import json
from pydantic_ai import RunContext
from app.mcp.builtin.excel import ExcelProfileTool, ExcelLogicExtractTool, ExcelScriptScanTool, ExcelReadTool, ExcelQueryTool
from app.mcp.builtin.registry import builtin_tool_registry
import os
from unittest.mock import MagicMock, patch

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures/excel"))

@pytest.fixture
def mock_ctx():
    return MagicMock(spec=RunContext)

@pytest.fixture
def mock_doc_access():
    with patch("app.mcp.builtin.excel._get_doc_access") as m:
        m.return_value = ([FIXTURES_DIR], [])
        yield m

@pytest.mark.asyncio
async def test_excel_profile_tool(mock_ctx, mock_doc_access):
    tool = ExcelProfileTool()
    args = {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_profile"
    assert "sheets" in resp

@pytest.mark.asyncio
async def test_excel_logic_extract_tool(mock_ctx, mock_doc_access):
    tool = ExcelLogicExtractTool()
    args = {"path": "logic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_logic_extract"
    assert "formulas" in resp
    assert "lineage" in resp

@pytest.mark.asyncio
async def test_excel_script_scan_tool(mock_ctx, mock_doc_access):
    tool = ExcelScriptScanTool()
    args = {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_script_scan"
    assert resp["has_macro"] is False

@pytest.mark.asyncio
async def test_excel_read_tool(mock_ctx, mock_doc_access):
    tool = ExcelReadTool()
    args = {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_read"
    assert "data" in resp

@pytest.mark.asyncio
async def test_excel_query_tool(mock_ctx, mock_doc_access):
    tool = ExcelQueryTool()
    args = {"path": "basic.xlsx", "query": "SELECT * FROM excel_data", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_query"
    assert "data" in resp

def test_registry_contains_excel_tools():
    all_tools = builtin_tool_registry.get_all_tools()
    tool_names = [t.name for t in all_tools]
    assert "excel_profile" in tool_names
    assert "excel_logic_extract" in tool_names
    assert "excel_script_scan" in tool_names
    assert "excel_read" in tool_names
    assert "excel_query" in tool_names


def test_get_doc_access_uses_config_service_roots_entrypoint():
    with patch("app.mcp.builtin.excel.config_service.get_doc_access_roots", return_value=(["/a"], ["/b"])) as getter:
        with patch("app.mcp.builtin.excel.config_service.get_config", return_value={"doc_access": {"allow_roots": ["/wrong"], "deny_roots": ["/wrong"]}}):
            from app.mcp.builtin.excel import _get_doc_access
            allow_roots, deny_roots = _get_doc_access()
    getter.assert_called_once()
    assert allow_roots == ["/a"]
    assert deny_roots == ["/b"]

@pytest.mark.asyncio
async def test_excel_profile_error_handling(mock_ctx, mock_doc_access):
    tool = ExcelProfileTool()
    # File does not exist
    args = {"path": "non_existent.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is False
    assert "error_code" in resp
    assert "message" in resp
