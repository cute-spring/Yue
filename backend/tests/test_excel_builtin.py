import pytest
import json
from pydantic_ai import RunContext
from app.mcp.builtin.excel import ExcelProfileTool, ExcelLogicExtractTool, ExcelScriptScanTool, ExcelReadTool, ExcelQueryTool
from app.mcp.builtin.registry import builtin_tool_registry
from unittest.mock import MagicMock, patch

FIXTURES_DIR = "/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/fixtures/excel"

@pytest.fixture
def mock_ctx():
    return MagicMock(spec=RunContext)

@pytest.fixture(autouse=True)
def mock_doc_access():
    with patch("app.mcp.builtin.excel._get_doc_access") as m:
        m.return_value = ([FIXTURES_DIR], [])
        yield m

@pytest.mark.asyncio
async def test_excel_profile_tool(mock_ctx):
    tool = ExcelProfileTool()
    args = {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_profile"
    assert "sheets" in resp

@pytest.mark.asyncio
async def test_excel_logic_extract_tool(mock_ctx):
    tool = ExcelLogicExtractTool()
    args = {"path": "logic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_logic_extract"
    assert "formulas" in resp
    assert "lineage" in resp

@pytest.mark.asyncio
async def test_excel_script_scan_tool(mock_ctx):
    tool = ExcelScriptScanTool()
    args = {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_script_scan"
    assert resp["has_macro"] is False

@pytest.mark.asyncio
async def test_excel_read_tool(mock_ctx):
    tool = ExcelReadTool()
    args = {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is True
    assert resp["tool"] == "excel_read"
    assert "data" in resp

@pytest.mark.asyncio
async def test_excel_query_tool(mock_ctx):
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

@pytest.mark.asyncio
async def test_excel_profile_error_handling(mock_ctx):
    tool = ExcelProfileTool()
    # File does not exist
    args = {"path": "non_existent.xlsx", "root_dir": FIXTURES_DIR}
    resp_str = await tool.execute(mock_ctx, args)
    resp = json.loads(resp_str)
    assert resp["ok"] is False
    assert "error_code" in resp
    assert "message" in resp
