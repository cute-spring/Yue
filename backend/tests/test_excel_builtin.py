import pytest
import json
from pydantic_ai import RunContext
from app.mcp.builtin.excel import ExcelProfileTool, ExcelLogicExtractTool, ExcelScriptScanTool, ExcelReadTool, ExcelQueryTool
from app.mcp.builtin.registry import builtin_tool_registry
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch
from app.services.config_service import ConfigService

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


@pytest.mark.asyncio
async def test_excel_tool_reads_doc_access_each_call_for_immediate_effect(mock_ctx):
    tool = ExcelProfileTool()
    with patch(
        "app.mcp.builtin.excel._get_doc_access",
        side_effect=[([FIXTURES_DIR], []), ([], [])],
    ):
        first = json.loads(await tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))
        second = json.loads(await tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))
    assert first["ok"] is True
    assert second["ok"] is False


@pytest.mark.asyncio
async def test_excel_read_and_query_immediate_effect_via_real_config_service_update(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        service = ConfigService(os.path.join(tmp, "global_config.json"))
        service.update_doc_access({"allow_roots": [FIXTURES_DIR], "deny_roots": []})

        read_tool = ExcelReadTool()
        query_tool = ExcelQueryTool()
        with patch("app.mcp.builtin.excel.config_service", service):
            first_read = json.loads(await read_tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))
            first_query = json.loads(
                await query_tool.execute(
                    mock_ctx,
                    {"path": "basic.xlsx", "query": "SELECT * FROM excel_data", "root_dir": FIXTURES_DIR},
                )
            )
            service.update_doc_access({"allow_roots": [], "deny_roots": []})
            second_read = json.loads(await read_tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))
            second_query = json.loads(
                await query_tool.execute(
                    mock_ctx,
                    {"path": "basic.xlsx", "query": "SELECT * FROM excel_data", "root_dir": FIXTURES_DIR},
                )
            )

    assert first_read["ok"] is True
    assert first_query["ok"] is True
    assert second_read["ok"] is False
    assert second_query["ok"] is False


@pytest.mark.asyncio
async def test_excel_read_reports_ambiguous_relative_path_when_multi_allow_roots(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        root_a = os.path.join(tmp, "a")
        root_b = os.path.join(tmp, "b")
        os.makedirs(root_a, exist_ok=True)
        os.makedirs(root_b, exist_ok=True)
        shutil.copyfile(os.path.join(FIXTURES_DIR, "basic.xlsx"), os.path.join(root_a, "dup.xlsx"))
        shutil.copyfile(os.path.join(FIXTURES_DIR, "basic.xlsx"), os.path.join(root_b, "dup.xlsx"))

        service = ConfigService(os.path.join(tmp, "global_config.json"))
        service.update_doc_access({"allow_roots": [root_a, root_b], "deny_roots": []})

        read_tool = ExcelReadTool()
        with patch("app.mcp.builtin.excel.config_service", service):
            payload = json.loads(await read_tool.execute(mock_ctx, {"path": "dup.xlsx"}))

    assert payload["ok"] is False
    assert payload["error_code"] == "EXCEL_READ_FAILED"
    assert "Ambiguous" in payload["message"]


@pytest.mark.asyncio
async def test_excel_profile_logic_script_immediate_effect_via_real_config_service_update(mock_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        service = ConfigService(os.path.join(tmp, "global_config.json"))
        service.update_doc_access({"allow_roots": [FIXTURES_DIR], "deny_roots": []})

        profile_tool = ExcelProfileTool()
        logic_tool = ExcelLogicExtractTool()
        script_tool = ExcelScriptScanTool()
        with patch("app.mcp.builtin.excel.config_service", service):
            first_profile = json.loads(await profile_tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))
            first_logic = json.loads(await logic_tool.execute(mock_ctx, {"path": "logic.xlsx", "root_dir": FIXTURES_DIR}))
            first_script = json.loads(await script_tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))

            service.update_doc_access({"allow_roots": [], "deny_roots": []})

            second_profile = json.loads(await profile_tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))
            second_logic = json.loads(await logic_tool.execute(mock_ctx, {"path": "logic.xlsx", "root_dir": FIXTURES_DIR}))
            second_script = json.loads(await script_tool.execute(mock_ctx, {"path": "basic.xlsx", "root_dir": FIXTURES_DIR}))

    assert first_profile["ok"] is True
    assert first_logic["ok"] is True
    assert first_script["ok"] is True
    assert second_profile["ok"] is False
    assert second_logic["ok"] is False
    assert second_script["ok"] is False
