import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from app.mcp.builtin.browser import BrowserBuiltinTool, browser_tool_contracts
from app.mcp.builtin.registry import builtin_tool_registry


@pytest.fixture
def mock_ctx():
    return MagicMock(spec=RunContext)


def _mock_playwright_page(*, url: str = "https://example.com/", title: str = "Example Domain") -> MagicMock:
    page = MagicMock()
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value=title)
    type(page).url = property(lambda self: url)
    return page


def _mock_playwright_context(monkeypatch, page: MagicMock):
    browser = MagicMock()
    browser.new_page = AsyncMock(return_value=page)
    browser.close = AsyncMock()

    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=browser)

    playwright = MagicMock()
    playwright.chromium = chromium

    class _PlaywrightContext:
        async def __aenter__(self):
            return playwright

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.mcp.builtin.browser.async_playwright", lambda: _PlaywrightContext())
    return chromium, browser


def _assert_success_payload_contract(payload, *, operation: str):
    assert payload["ok"] is True
    assert payload["tool"] == f"browser_{operation}"
    assert payload["operation"] == operation
    assert payload["status"] == "succeeded"
    assert payload["error_code"] is None
    assert payload["metadata"] == {
        "contract_version": 1,
        "tool_family": "agent_browser",
        "platform_owned": True,
        "runtime_boundary": "builtin_tool_only",
        "execution_engine": "playwright",
    }


def test_registry_contains_browser_builtin_contract_tools():
    tool_names = [tool.name for tool in builtin_tool_registry.get_all_tools()]

    assert "browser_open" in tool_names
    assert "browser_snapshot" in tool_names
    assert "browser_click" in tool_names
    assert "browser_type" in tool_names
    assert "browser_press" in tool_names
    assert "browser_screenshot" in tool_names


def test_browser_builtin_metadata_exposes_contract_fields():
    metadata = {
        item["name"]: item
        for item in builtin_tool_registry.get_all_metadata()
        if item["name"].startswith("browser_")
    }

    click_meta = metadata["browser_click"]
    assert click_meta["id"] == "builtin:browser_click"
    assert click_meta["metadata"]["tool_family"] == "agent_browser"
    assert click_meta["metadata"]["operation"] == "click"
    assert click_meta["metadata"]["recommended_approval_policy"] == "manual"
    assert click_meta["metadata"]["execution_engine"] == "playwright"
    assert click_meta["input_schema"]["required"] == ["element_ref"]
    assert "binding_source" in click_meta["input_schema"]["properties"]
    assert "url" in click_meta["input_schema"]["properties"]
    assert click_meta["output_schema"]["properties"]["status"]["enum"] == ["succeeded", "failed", "not_implemented"]
    assert click_meta["metadata"]["runtime_metadata_expectations"]["optional"] == [
        "session_id",
        "tab_id",
        "url",
        "binding_source",
        "binding_session_id",
        "binding_tab_id",
        "binding_url",
        "binding_dom_version",
        "active_dom_version",
    ]
    assert click_meta["metadata"]["structured_failure_codes"] == [
        "browser_session_required",
        "browser_tab_required",
        "browser_target_required",
        "browser_target_stale",
        "browser_target_context_mismatch",
    ]
    assert click_meta["metadata"]["continuity"] == {
        "contract_mode": "authoritative_target_mutation",
        "authoritative_target_required": True,
        "resumable_continuity": "deferred",
        "current_execution_mode": "single_use_url_scoped",
    }

    open_meta = metadata["browser_open"]
    assert open_meta["metadata"]["recommended_approval_policy"] == "auto"
    assert open_meta["input_schema"]["required"] == ["url"]
    assert open_meta["metadata"]["execution_engine"] == "playwright"
    assert open_meta["metadata"]["continuity"] == {
        "contract_mode": "single_use_url_scoped",
        "authoritative_target_required": False,
        "resumable_continuity": "not_required",
    }

    snapshot_meta = metadata["browser_snapshot"]
    assert "url" in snapshot_meta["input_schema"]["properties"]
    assert snapshot_meta["input_schema"]["required"] == ["url"]
    assert snapshot_meta["metadata"]["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
    ]
    assert snapshot_meta["metadata"]["runtime_metadata_expectations"]["optional"] == [
        "session_id",
        "tab_id",
        "url",
        "wait_until",
        "max_nodes",
        "binding_source",
        "binding_session_id",
        "binding_tab_id",
        "binding_url",
        "binding_dom_version",
    ]
    interactive_item = snapshot_meta["output_schema"]["properties"]["snapshot"]["properties"]["interactive_elements"]["items"]
    assert interactive_item["properties"]["target_binding"]["required"] == [
        "binding_source",
        "binding_session_id",
        "binding_tab_id",
        "binding_url",
        "binding_dom_version",
    ]
    assert snapshot_meta["output_schema"]["properties"]["snapshot"]["properties"]["target_binding_context"]["type"] == [
        "object",
        "null",
    ]

    screenshot_meta = metadata["browser_screenshot"]
    assert screenshot_meta["metadata"]["execution_engine"] == "playwright"
    assert "url" in screenshot_meta["input_schema"]["properties"]
    assert screenshot_meta["input_schema"]["required"] == ["url"]
    assert screenshot_meta["metadata"]["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
    ]
    assert screenshot_meta["metadata"]["runtime_metadata_expectations"]["optional"] == [
        "session_id",
        "tab_id",
        "url",
        "wait_until",
        "label",
    ]

    press_meta = metadata["browser_press"]
    assert press_meta["metadata"]["execution_engine"] == "playwright"
    assert "url" in press_meta["input_schema"]["properties"]
    assert press_meta["input_schema"]["required"] == ["url", "key"]
    assert press_meta["metadata"]["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
        "key",
    ]
    assert press_meta["metadata"]["runtime_metadata_expectations"]["optional"] == [
        "session_id",
        "tab_id",
        "url",
        "wait_until",
        "element_ref",
    ]
    type_meta = metadata["browser_type"]
    assert type_meta["metadata"]["execution_engine"] == "playwright"
    assert "url" in type_meta["input_schema"]["properties"]
    assert type_meta["metadata"]["structured_failure_codes"] == [
        "browser_session_required",
        "browser_tab_required",
        "browser_target_required",
        "browser_target_stale",
        "browser_target_context_mismatch",
    ]
    assert type_meta["metadata"]["continuity"] == {
        "contract_mode": "authoritative_target_mutation",
        "authoritative_target_required": True,
        "resumable_continuity": "deferred",
        "current_execution_mode": "single_use_url_scoped",
    }


def test_browser_tool_contracts_define_output_schema_and_runtime_metadata_expectations():
    tool_map = {tool.name: tool for tool in browser_tool_contracts}

    assert isinstance(tool_map["browser_open"], BrowserBuiltinTool)
    assert tool_map["browser_screenshot"].output_schema["properties"]["artifact"]["type"] == ["object", "null"]
    assert "binding_source" in tool_map["browser_click"].parameters["properties"]
    assert "active_dom_version" in tool_map["browser_click"].parameters["properties"]
    assert tool_map["browser_click"].contract_metadata["continuity"]["contract_mode"] == "authoritative_target_mutation"
    assert tool_map["browser_type"].contract_metadata["runtime_metadata_expectations"]["required"] == [
        "operation",
        "element_ref",
    ]
    assert "binding_source" in tool_map["browser_type"].parameters["properties"]
    assert "url" in tool_map["browser_type"].parameters["properties"]
    assert tool_map["browser_press"].contract_metadata["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
        "key",
    ]


@pytest.mark.asyncio
async def test_browser_builtin_returns_placeholder_not_implemented_payload(mock_ctx):
    tool = BrowserBuiltinTool(
        name="browser_placeholder",
        description="placeholder browser op",
        operation="placeholder",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        recommended_approval_policy="manual",
        runtime_metadata_expectations={"required": ["operation"], "optional": []},
    )

    result = await tool.execute(
        mock_ctx,
        {
            "session_id": "session-1",
            "tab_id": "tab-1",
            "include_text": True,
            "max_nodes": 20,
        },
    )

    payload = json.loads(result)
    assert payload["ok"] is False
    assert payload["tool"] == "browser_placeholder"
    assert payload["operation"] == "placeholder"
    assert payload["status"] == "not_implemented"
    assert payload["error_code"] == "browser_not_implemented"
    assert payload["browser_context"]["session_id"] == "session-1"
    assert payload["browser_context"]["tab_id"] == "tab-1"
    assert payload["snapshot"]["max_nodes"] == 20
    assert payload["metadata"]["tool_family"] == "agent_browser"
    assert payload["metadata"]["execution_engine"] == "placeholder"


@pytest.mark.asyncio
async def test_browser_open_executes_with_ephemeral_playwright_flow(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_open")
    assert tool is not None

    page = _mock_playwright_page()
    chromium, browser = _mock_playwright_context(monkeypatch, page)

    result = await tool.execute(
        mock_ctx,
        {"url": "https://example.com", "session_id": "session-1", "tab_id": "tab-1"},
    )

    payload = json.loads(result)
    _assert_success_payload_contract(payload, operation="open")
    assert payload["browser_context"]["url"] == "https://example.com/"
    assert payload["browser_context"]["page_title"] == "Example Domain"
    assert payload["artifact"] == {"kind": None, "label": None, "path": None}
    assert payload["snapshot"] == {
        "interactive_elements": None,
        "visible_text": None,
        "max_nodes": None,
        "target_binding_context": None,
    }
    chromium.launch.assert_awaited_once_with(headless=True)
    page.goto.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_open_raises_runtime_error_when_playwright_fails(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_open")
    assert tool is not None

    chromium = MagicMock()
    chromium.launch = AsyncMock(side_effect=RuntimeError("missing browser executable"))

    playwright = MagicMock()
    playwright.chromium = chromium

    class _PlaywrightContext:
        async def __aenter__(self):
            return playwright

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.mcp.builtin.browser.async_playwright", lambda: _PlaywrightContext())

    with pytest.raises(RuntimeError, match="browser_open failed"):
        await tool.execute(mock_ctx, {"url": "https://example.com"})


@pytest.mark.asyncio
async def test_browser_snapshot_executes_with_single_use_url(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_snapshot")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(
        return_value={
            "interactive_elements": [
                {
                    "ref": "snapshot:browser_snapshot#node:1",
                    "tag": "a",
                    "text": "More information",
                    "aria_label": None,
                    "name": None,
                    "id": "more-info-link",
                    "target_binding": {
                        "binding_source": "snapshot:browser_snapshot",
                        "binding_session_id": "session-1",
                        "binding_tab_id": "tab-1",
                        "binding_url": "https://example.com/",
                        "binding_dom_version": None,
                    },
                }
            ],
            "visible_text": "Example Domain body text",
            "max_nodes": 20,
            "target_binding_context": {
                "binding_source": "snapshot:browser_snapshot",
                "binding_session_id": "session-1",
                "binding_tab_id": "tab-1",
                "binding_url": "https://example.com/",
                "binding_dom_version": None,
            },
        }
    )
    _mock_playwright_context(monkeypatch, page)

    result = await tool.execute(
        mock_ctx,
        {
            "url": "https://example.com",
            "session_id": "session-1",
            "tab_id": "tab-1",
            "include_text": True,
            "include_interactive_elements": True,
            "max_nodes": 20,
        },
    )

    payload = json.loads(result)
    _assert_success_payload_contract(payload, operation="snapshot")
    assert payload["browser_context"]["url"] == "https://example.com/"
    assert payload["browser_context"]["page_title"] == "Example Domain"
    assert payload["artifact"] == {"kind": None, "label": None, "path": None}
    assert payload["snapshot"]["visible_text"] == "Example Domain body text"
    assert payload["snapshot"]["interactive_elements"][0]["ref"] == "snapshot:browser_snapshot#node:1"
    assert payload["snapshot"]["interactive_elements"][0]["target_binding"] == {
        "binding_source": "snapshot:browser_snapshot",
        "binding_session_id": "session-1",
        "binding_tab_id": "tab-1",
        "binding_url": "https://example.com/",
        "binding_dom_version": None,
    }
    assert payload["snapshot"]["target_binding_context"] == {
        "binding_source": "snapshot:browser_snapshot",
        "binding_session_id": "session-1",
        "binding_tab_id": "tab-1",
        "binding_url": "https://example.com/",
        "binding_dom_version": None,
    }
    page.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_snapshot_requires_url_until_session_persistence_exists(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_snapshot")
    assert tool is not None

    with pytest.raises(RuntimeError, match="requires `url` until persistent browser sessions are implemented"):
        await tool.execute(mock_ctx, {"include_text": True})


@pytest.mark.asyncio
async def test_browser_click_executes_with_single_use_url_and_minted_target(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_click")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(return_value={"clicked": True, "text": "More information"})
    page.wait_for_load_state = AsyncMock()
    chromium, browser = _mock_playwright_context(monkeypatch, page)

    result = await tool.execute(
        mock_ctx,
        {
            "url": "https://example.com",
            "element_ref": "snapshot:browser_snapshot#node:1",
            "binding_source": "snapshot:browser_snapshot",
            "wait_after": True,
        },
    )

    payload = json.loads(result)
    _assert_success_payload_contract(payload, operation="click")
    assert payload["browser_context"]["url"] == "https://example.com/"
    assert payload["browser_context"]["page_title"] == "Example Domain"
    assert payload["target"] == {
        "element_ref": "snapshot:browser_snapshot#node:1",
        "text": "More information",
        "key": None,
    }
    assert payload["artifact"] == {"kind": None, "label": None, "path": None}
    assert payload["snapshot"] == {
        "interactive_elements": None,
        "visible_text": None,
        "max_nodes": None,
        "target_binding_context": None,
    }
    chromium.launch.assert_awaited_once_with(headless=True)
    page.goto.assert_awaited_once()
    page.evaluate.assert_awaited_once()
    page.wait_for_load_state.assert_awaited_once_with("load", timeout=3000)
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_click_requires_url_until_session_persistence_exists(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_click")
    assert tool is not None

    with pytest.raises(RuntimeError, match="requires `url` until persistent browser sessions are implemented"):
        await tool.execute(
            mock_ctx,
            {
                "element_ref": "snapshot:browser_snapshot#node:1",
                "binding_source": "snapshot:browser_snapshot",
            },
        )


@pytest.mark.asyncio
async def test_browser_click_rejects_resumable_continuity_context_without_restore_backend(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_click")
    assert tool is not None

    with pytest.raises(RuntimeError, match="received resumable continuity context"):
        await tool.execute(
            mock_ctx,
            {
                "session_id": "session-1",
                "tab_id": "tab-1",
                "element_ref": "snapshot:browser_snapshot#node:1",
                "binding_source": "snapshot:browser_snapshot",
            },
        )


@pytest.mark.asyncio
async def test_browser_click_rejects_non_minted_target_ref(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_click")
    assert tool is not None

    with pytest.raises(RuntimeError, match="does not match binding_source"):
        await tool.execute(
            mock_ctx,
            {
                "url": "https://example.com",
                "element_ref": "node:1",
                "binding_source": "snapshot:browser_snapshot",
            },
        )


@pytest.mark.asyncio
async def test_browser_click_raises_when_minted_target_cannot_be_resolved(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_click")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(return_value={"clicked": False, "text": None})
    page.wait_for_load_state = AsyncMock()
    _mock_playwright_context(monkeypatch, page)

    with pytest.raises(RuntimeError, match="could not resolve minted target"):
        await tool.execute(
            mock_ctx,
            {
                "url": "https://example.com",
                "element_ref": "snapshot:browser_snapshot#node:9",
                "binding_source": "snapshot:browser_snapshot",
                "wait_after": False,
            },
        )


@pytest.mark.asyncio
async def test_browser_click_skips_wait_after_when_disabled(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_click")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(return_value={"clicked": True, "text": "More information"})
    page.wait_for_load_state = AsyncMock()
    _mock_playwright_context(monkeypatch, page)

    result = await tool.execute(
        mock_ctx,
        {
            "url": "https://example.com",
            "element_ref": "snapshot:browser_snapshot#node:1",
            "binding_source": "snapshot:browser_snapshot",
            "wait_after": False,
        },
    )

    payload = json.loads(result)
    assert payload["ok"] is True
    page.wait_for_load_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_browser_type_executes_with_single_use_url_and_minted_target(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_type")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(return_value={"typed": True, "tag": "input"})
    chromium, browser = _mock_playwright_context(monkeypatch, page)

    result = await tool.execute(
        mock_ctx,
        {
            "url": "https://example.com",
            "element_ref": "snapshot:browser_snapshot#node:2",
            "binding_source": "snapshot:browser_snapshot",
            "text": "hello",
            "clear_first": True,
        },
    )

    payload = json.loads(result)
    _assert_success_payload_contract(payload, operation="type")
    assert payload["browser_context"]["url"] == "https://example.com/"
    assert payload["browser_context"]["page_title"] == "Example Domain"
    assert payload["target"] == {
        "element_ref": "snapshot:browser_snapshot#node:2",
        "text": "hello",
        "key": None,
    }
    assert payload["artifact"] == {"kind": None, "label": None, "path": None}
    assert payload["snapshot"] == {
        "interactive_elements": None,
        "visible_text": None,
        "max_nodes": None,
        "target_binding_context": None,
    }
    chromium.launch.assert_awaited_once_with(headless=True)
    page.goto.assert_awaited_once()
    page.evaluate.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_type_requires_url_until_session_persistence_exists(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_type")
    assert tool is not None

    with pytest.raises(RuntimeError, match="requires `url` until persistent browser sessions are implemented"):
        await tool.execute(
            mock_ctx,
            {
                "element_ref": "snapshot:browser_snapshot#node:2",
                "binding_source": "snapshot:browser_snapshot",
                "text": "hello",
            },
        )


@pytest.mark.asyncio
async def test_browser_type_rejects_resumable_continuity_context_without_restore_backend(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_type")
    assert tool is not None

    with pytest.raises(RuntimeError, match="received resumable continuity context"):
        await tool.execute(
            mock_ctx,
            {
                "session_id": "session-1",
                "tab_id": "tab-1",
                "element_ref": "snapshot:browser_snapshot#node:2",
                "binding_source": "snapshot:browser_snapshot",
                "text": "hello",
            },
        )


@pytest.mark.asyncio
async def test_browser_type_rejects_non_minted_target_ref(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_type")
    assert tool is not None

    with pytest.raises(RuntimeError, match="does not match binding_source"):
        await tool.execute(
            mock_ctx,
            {
                "url": "https://example.com",
                "element_ref": "node:2",
                "binding_source": "snapshot:browser_snapshot",
                "text": "hello",
            },
        )


@pytest.mark.asyncio
async def test_browser_type_raises_when_minted_target_cannot_be_resolved(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_type")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(return_value={"typed": False, "tag": None})
    _mock_playwright_context(monkeypatch, page)

    with pytest.raises(RuntimeError, match="could not resolve minted target"):
        await tool.execute(
            mock_ctx,
            {
                "url": "https://example.com",
                "element_ref": "snapshot:browser_snapshot#node:9",
                "binding_source": "snapshot:browser_snapshot",
                "text": "hello",
            },
        )


@pytest.mark.asyncio
async def test_browser_type_raises_when_minted_target_is_not_a_form_field(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_type")
    assert tool is not None

    page = _mock_playwright_page()
    page.evaluate = AsyncMock(return_value={"typed": False, "tag": "button"})
    _mock_playwright_context(monkeypatch, page)

    with pytest.raises(RuntimeError, match="could not resolve minted target"):
        await tool.execute(
            mock_ctx,
            {
                "url": "https://example.com",
                "element_ref": "snapshot:browser_snapshot#node:2",
                "binding_source": "snapshot:browser_snapshot",
                "text": "hello",
                "clear_first": False,
            },
        )


@pytest.mark.asyncio
async def test_browser_screenshot_executes_with_single_use_url(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_screenshot")
    assert tool is not None

    page = _mock_playwright_page()
    page.screenshot = AsyncMock()
    _mock_playwright_context(monkeypatch, page)
    monkeypatch.setattr("app.mcp.builtin.browser._resolve_exports_dir", lambda: "/tmp")
    monkeypatch.setattr(
        "app.mcp.builtin.browser.tempfile.mkstemp",
        lambda prefix, suffix, dir=None: (123, "/tmp/browser-shot.png"),
    )
    monkeypatch.setattr("app.mcp.builtin.browser.os.close", lambda fd: None)

    result = await tool.execute(
        mock_ctx,
        {
            "url": "https://example.com",
            "full_page": True,
            "label": "landing-page",
        },
    )

    payload = json.loads(result)
    _assert_success_payload_contract(payload, operation="screenshot")
    assert payload["browser_context"]["url"] == "https://example.com/"
    assert payload["browser_context"]["page_title"] == "Example Domain"
    assert payload["artifact"]["kind"] == "screenshot"
    assert payload["artifact"]["label"] == "landing-page"
    assert payload["artifact"]["path"] == "/tmp/browser-shot.png"
    assert payload["filename"] == "browser-shot.png"
    assert payload["file_path"] == "/tmp/browser-shot.png"
    assert payload["download_url"] == "/exports/browser-shot.png"
    assert payload["download_markdown"] == "[browser-shot.png](/exports/browser-shot.png)"
    assert payload["snapshot"] == {
        "interactive_elements": None,
        "visible_text": None,
        "max_nodes": None,
        "target_binding_context": None,
    }
    page.screenshot.assert_awaited_once_with(path="/tmp/browser-shot.png", full_page=True)


@pytest.mark.asyncio
async def test_browser_screenshot_requires_url_until_session_persistence_exists(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_screenshot")
    assert tool is not None

    with pytest.raises(RuntimeError, match="requires `url` until persistent browser sessions are implemented"):
        await tool.execute(mock_ctx, {"label": "example"})


@pytest.mark.asyncio
async def test_browser_press_executes_with_single_use_url(mock_ctx, monkeypatch):
    tool = builtin_tool_registry.get_tool("browser_press")
    assert tool is not None

    page = _mock_playwright_page()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    chromium, browser = _mock_playwright_context(monkeypatch, page)

    result = await tool.execute(
        mock_ctx,
        {
            "url": "https://example.com",
            "key": "Enter",
            "element_ref": "node:1",
        },
    )

    payload = json.loads(result)
    _assert_success_payload_contract(payload, operation="press")
    assert payload["browser_context"]["url"] == "https://example.com/"
    assert payload["browser_context"]["page_title"] == "Example Domain"
    assert payload["target"] == {"element_ref": "node:1", "text": None, "key": "Enter"}
    assert payload["artifact"] == {"kind": None, "label": None, "path": None}
    assert payload["snapshot"] == {
        "interactive_elements": None,
        "visible_text": None,
        "max_nodes": None,
        "target_binding_context": None,
    }
    chromium.launch.assert_awaited_once_with(headless=True)
    page.goto.assert_awaited_once()
    page.keyboard.press.assert_awaited_once_with("Enter")
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_press_requires_url_until_session_persistence_exists(mock_ctx):
    tool = builtin_tool_registry.get_tool("browser_press")
    assert tool is not None

    with pytest.raises(RuntimeError, match="requires `url` until persistent browser sessions are implemented"):
        await tool.execute(mock_ctx, {"key": "Enter"})


def test_browser_read_only_tool_contracts_share_kernel_friendly_result_shape():
    tool_map = {tool.name: tool for tool in browser_tool_contracts}

    for tool_name in ("browser_open", "browser_snapshot", "browser_screenshot"):
        tool = tool_map[tool_name]
        assert tool.output_schema["required"] == [
            "ok",
            "tool",
            "operation",
            "status",
            "error_code",
            "message",
            "browser_context",
            "target",
            "artifact",
            "snapshot",
            "metadata",
            "filename",
            "file_path",
            "download_url",
            "download_markdown",
        ]
        assert tool.output_schema["properties"]["metadata"]["required"] == [
            "contract_version",
            "tool_family",
            "platform_owned",
            "runtime_boundary",
            "execution_engine",
        ]
        assert tool.output_schema["properties"]["browser_context"]["required"] == [
            "session_id",
            "tab_id",
            "url",
            "page_title",
        ]
        assert tool.contract_metadata["tool_family"] == "agent_browser"
        assert tool.contract_metadata["platform_boundary"] == "builtin_tool_only"
        assert tool.contract_metadata["execution_engine"] == "playwright"


def test_browser_press_contract_reuses_shared_kernel_friendly_result_shape():
    tool_map = {tool.name: tool for tool in browser_tool_contracts}
    tool = tool_map["browser_press"]

    assert tool.output_schema["required"] == [
        "ok",
        "tool",
        "operation",
        "status",
        "error_code",
        "message",
        "browser_context",
        "target",
        "artifact",
        "snapshot",
        "metadata",
        "filename",
        "file_path",
        "download_url",
        "download_markdown",
    ]
    assert tool.contract_metadata["tool_family"] == "agent_browser"
    assert tool.contract_metadata["platform_boundary"] == "builtin_tool_only"
    assert tool.contract_metadata["execution_engine"] == "playwright"
