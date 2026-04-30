import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from pydantic_ai import RunContext

from app.main import app
from app.mcp.builtin.docs import DocsListTool
from app.services.config_service import ConfigService


def test_doc_access_api_update_takes_effect_on_next_docs_tool_call():
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

        ctx = MagicMock(spec=RunContext)
        ctx.deps = {"citations": []}
        tool = DocsListTool()

        with patch("app.api.config.config_service", service), patch("app.mcp.builtin.docs.config_service", service):
            client = TestClient(app)
            first = json.loads(_run(tool, ctx))
            resp = client.post("/api/config/doc_access", json={"allow_roots": [root_b], "deny_roots": []})
            assert resp.status_code == 200
            second = json.loads(_run(tool, ctx))

        assert first[0]["root"] == os.path.realpath(root_a)
        assert any(item["path"] == "a.txt" for item in first[0]["items"])
        assert second[0]["root"] == os.path.realpath(root_b)
        assert any(item["path"] == "b.txt" for item in second[0]["items"])


def _run(tool: DocsListTool, ctx: RunContext) -> str:
    import asyncio

    return asyncio.run(tool.execute(ctx, {}))
