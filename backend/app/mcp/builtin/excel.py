import json
import logging
from typing import Any, Dict, List, Optional
from pydantic_ai import RunContext

from app.services.excel_service import excel_service
from app.services.config_service import config_service
from ..base import BaseTool
from .registry import builtin_tool_registry

logger = logging.getLogger(__name__)

def _get_doc_access() -> tuple[List[str], List[str]]:
    return config_service.get_doc_access_roots()

class ExcelProfileTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="excel_profile",
            description=(
                "Identify the structural metadata of an Excel or CSV file. "
                "Use this tool FIRST when encountering a new file to understand its sheets, "
                "header locations, data blocks, merged cells, and hidden rows/columns. "
                "This helps in deciding whether to use excel_read or excel_query."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Excel (.xlsx, .xlsm, .xltx, .xltm) or CSV file."
                    },
                    "root_dir": {
                        "type": "string",
                        "description": "Optional root directory for path resolution."
                    },
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        root_dir = args.get("root_dir")
        allow_roots, deny_roots = _get_doc_access()
        # Try to get request_id from context if available
        request_id = getattr(ctx, "request_id", None)
        
        try:
            result = excel_service.profile(path, root_dir, allow_roots, deny_roots, request_id=request_id)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error profiling Excel: {e}")
            return json.dumps({
                "ok": False,
                "error_code": "EXCEL_PROFILE_FAILED",
                "message": str(e),
                "hint": "Check if the file exists and is a valid Excel/CSV format. Try specifying a root_dir if the path is relative."
            }, ensure_ascii=False, indent=2)

class ExcelLogicExtractTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="excel_logic_extract",
            description=(
                "Extract business logic from an Excel file, including formulas, "
                "cell dependencies (lineage), named ranges, data validations, and external connections. "
                "Use this when you need to understand HOW values are calculated or what rules apply to the data."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the Excel file."},
                    "sheet_name": {"type": "string", "description": "Optional specific sheet name to analyze."},
                    "root_dir": {"type": "string", "description": "Optional root directory."},
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        sheet_name = args.get("sheet_name")
        root_dir = args.get("root_dir")
        allow_roots, deny_roots = _get_doc_access()
        request_id = getattr(ctx, "request_id", None)
        
        try:
            result = excel_service.logic_extract(path, sheet_name, root_dir, allow_roots, deny_roots, request_id=request_id)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error extracting Excel logic: {e}")
            return json.dumps({
                "ok": False,
                "error_code": "EXCEL_LOGIC_EXTRACT_FAILED",
                "message": str(e),
                "hint": "Ensure the file is a modern Excel format (.xlsx, .xlsm). Formulas cannot be extracted from CSV files."
            }, ensure_ascii=False, indent=2)

class ExcelScriptScanTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="excel_script_scan",
            description=(
                "Perform a static security scan for VBA macros and embedded scripts in Excel files. "
                "Use this BEFORE opening or processing files from untrusted sources to identify potential risks. "
                "It detects suspicious keywords like 'Shell', 'CreateObject', etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the Excel file."},
                    "root_dir": {"type": "string", "description": "Optional root directory."},
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        root_dir = args.get("root_dir")
        allow_roots, deny_roots = _get_doc_access()
        request_id = getattr(ctx, "request_id", None)
        
        try:
            result = excel_service.script_scan(path, root_dir, allow_roots, deny_roots, request_id=request_id)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error scanning Excel script: {e}")
            return json.dumps({
                "ok": False,
                "error_code": "EXCEL_SCRIPT_SCAN_FAILED",
                "message": str(e),
                "hint": "Static scan is only supported for .xlsx, .xlsm, and other ZIP-based Office formats."
            }, ensure_ascii=False, indent=2)

class ExcelReadTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="excel_read",
            description=(
                "Read raw data from a specific sheet or cell range in an Excel or CSV file. "
                "Use this for direct data inspection or when you need to see a small slice of data. "
                "For large datasets requiring filtering or aggregation, use excel_query instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "sheet_name": {"type": "string", "description": "Sheet name (defaults to the first sheet)."},
                    "range": {"type": "string", "description": "Optional cell range (e.g., 'A1:C20')."},
                    "mode": {
                        "type": "string", 
                        "enum": ["json", "markdown"], 
                        "default": "json",
                        "description": "Output format. Use 'markdown' for better readability in chat."
                    },
                    "root_dir": {"type": "string", "description": "Optional root directory."},
                },
                "required": ["path"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        sheet_name = args.get("sheet_name")
        range_val = args.get("range")
        mode = args.get("mode", "json")
        root_dir = args.get("root_dir")
        allow_roots, deny_roots = _get_doc_access()
        request_id = getattr(ctx, "request_id", None)
        
        try:
            result = excel_service.read(path, sheet_name, range_val, mode, root_dir, allow_roots, deny_roots, request_id=request_id)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error reading Excel: {e}")
            return json.dumps({
                "ok": False,
                "error_code": "EXCEL_READ_FAILED",
                "message": str(e),
                "hint": "Check if the sheet name exists and the range is valid (e.g., 'A1:B10')."
            }, ensure_ascii=False, indent=2)

class ExcelQueryTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="excel_query",
            description=(
                "Execute high-performance SQL SELECT queries on Excel or CSV data. "
                "Use this for filtering, sorting, grouping, or joining data within a file. "
                "The data is loaded into a virtual table named 'excel_data'. "
                "Example: 'SELECT Department, SUM(Salary) FROM excel_data GROUP BY Department'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "query": {
                        "type": "string", 
                        "description": "SQL SELECT query to execute on the 'excel_data' table."
                    },
                    "sheet_name": {"type": "string", "description": "Sheet name to load as 'excel_data'."},
                    "root_dir": {"type": "string", "description": "Optional root directory."},
                },
                "required": ["path", "query"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        path = args.get("path")
        query = args.get("query")
        sheet_name = args.get("sheet_name")
        root_dir = args.get("root_dir")
        allow_roots, deny_roots = _get_doc_access()
        request_id = getattr(ctx, "request_id", None)
        
        try:
            result = excel_service.query(path, query, sheet_name, root_dir, allow_roots, deny_roots, request_id=request_id)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error querying Excel: {e}")
            return json.dumps({
                "ok": False,
                "error_code": "EXCEL_QUERY_FAILED",
                "message": str(e),
                "hint": "Only SELECT statements are supported. Ensure column names in your query match the headers in the file."
            }, ensure_ascii=False, indent=2)

# Register tools
builtin_tool_registry.register(ExcelProfileTool())
builtin_tool_registry.register(ExcelLogicExtractTool())
builtin_tool_registry.register(ExcelScriptScanTool())
builtin_tool_registry.register(ExcelReadTool())
builtin_tool_registry.register(ExcelQueryTool())
