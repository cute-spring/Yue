import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.mcp.builtin.ppt import GeneratePptxTool


def test_generate_pptx_uses_yue_data_dir_exports(tmp_path, monkeypatch):
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "runtime-data"))

    tool = GeneratePptxTool()
    captured = {}

    async def fake_communicate(input=None):
        captured["stdin"] = input
        return b"", b""

    fake_process = SimpleNamespace(returncode=0, communicate=AsyncMock(side_effect=fake_communicate))

    async def run_test():
        with patch("app.mcp.builtin.ppt.os.path.exists", return_value=True), \
             patch("app.mcp.builtin.ppt.asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake_process)):
            result = await tool.execute(
                SimpleNamespace(deps={}),
                {
                    "data": {
                        "title": "Product Update Platform Name",
                        "slides": [{"title": "Intro", "content": ["hello"]}],
                    }
                },
            )

        payload = json.loads(result)
        expected_exports_dir = (tmp_path / "runtime-data" / "exports").resolve()
        assert Path(payload["file_path"]).parent == expected_exports_dir
        assert payload["filename"] == "product_update_platform_name.pptx"
        assert payload["download_url"] == "/exports/product_update_platform_name.pptx"

        stdin_payload = json.loads(captured["stdin"].decode())
        assert Path(stdin_payload["output_file"]).parent == expected_exports_dir

    asyncio.run(run_test())
