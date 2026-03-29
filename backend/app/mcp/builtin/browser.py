import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic_ai import RunContext
try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without playwright installed
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None

from ..base import BaseTool
from .registry import builtin_tool_registry


BROWSER_CONTRACT_VERSION = 1
BROWSER_TOOL_FAMILY = "agent_browser"
BROWSER_RESULT_STATUSES = ["succeeded", "failed", "not_implemented"]
INTERACTIVE_SELECTOR = ",".join(
    [
        "a[href]",
        "button",
        "input",
        "textarea",
        "select",
        '[role="button"]',
        "[tabindex]",
    ]
)


def _require_playwright_dependency(tool_name: str) -> None:
    if async_playwright is None:
        raise RuntimeError(
            f"{tool_name} requires the optional `playwright` dependency, but it is not installed."
        )


def _common_browser_fields() -> Dict[str, Any]:
    return {
        "session_id": {
            "type": "string",
            "description": "Optional browser session identifier supplied by the platform runtime.",
        },
        "tab_id": {
            "type": "string",
            "description": "Optional browser tab identifier supplied by the platform runtime.",
        },
    }


def _resolve_exports_dir() -> str:
    data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
    exports_dir = data_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return str(exports_dir.resolve())


def _target_binding_fields() -> Dict[str, Any]:
    return {
        "binding_session_id": {
            "type": "string",
            "description": "Browser session identity expected by the minted target reference.",
        },
        "binding_source": {
            "type": "string",
            "description": "Opaque platform-issued binding source identifier for a minted target reference.",
        },
        "binding_tab_id": {
            "type": "string",
            "description": "Tab identity expected by the minted target reference.",
        },
        "binding_url": {
            "type": "string",
            "description": "URL observed when the target reference was minted.",
        },
        "binding_dom_version": {
            "type": "string",
            "description": "Optional DOM/version marker captured when the target reference was minted.",
        },
        "active_dom_version": {
            "type": "string",
            "description": "Optional current DOM/version marker supplied by the platform when validating a target-bound mutation.",
        },
    }


def _parse_minted_target_ref(element_ref: Any, binding_source: Any) -> int:
    if not isinstance(binding_source, str) or not binding_source.strip():
        raise RuntimeError("binding_source is required for authoritative browser targets")
    if not isinstance(element_ref, str) or not element_ref.strip():
        raise RuntimeError("element_ref is required for authoritative browser targets")

    prefix = f"{binding_source}#node:"
    if not element_ref.startswith(prefix):
        raise RuntimeError(
            f"element_ref `{element_ref}` does not match binding_source `{binding_source}`"
        )

    suffix = element_ref[len(prefix) :]
    try:
        node_index = int(suffix)
    except ValueError as exc:
        raise RuntimeError(f"element_ref `{element_ref}` is not a valid minted browser target") from exc
    if node_index < 1:
        raise RuntimeError(f"element_ref `{element_ref}` is not a valid minted browser target")
    return node_index


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_navigation_url(
    *,
    tool_name: str,
    args: Dict[str, Any],
    continuity_sensitive: bool = False,
) -> str:
    url = args.get("url")
    if _is_non_empty_string(url):
        return str(url).strip()

    has_session = _is_non_empty_string(args.get("session_id"))
    has_tab = _is_non_empty_string(args.get("tab_id"))
    has_target = _is_non_empty_string(args.get("element_ref"))
    if continuity_sensitive and has_session and has_tab and has_target:
        raise RuntimeError(
            f"{tool_name} received resumable continuity context (`session_id`, `tab_id`, `element_ref`) "
            "but persistent browser session restore is not implemented in this phase."
        )

    raise RuntimeError(f"{tool_name} requires `url` until persistent browser sessions are implemented.")


def _base_result_schema(operation: str) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "tool": {"type": "string"},
            "operation": {"type": "string", "enum": [operation]},
            "status": {"type": "string", "enum": BROWSER_RESULT_STATUSES},
            "error_code": {"type": ["string", "null"]},
            "message": {"type": "string"},
            "browser_context": {
                "type": "object",
                "properties": {
                    "session_id": {"type": ["string", "null"]},
                    "tab_id": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "page_title": {"type": ["string", "null"]},
                },
                "required": ["session_id", "tab_id", "url", "page_title"],
                "additionalProperties": False,
            },
            "target": {
                "type": ["object", "null"],
                "properties": {
                    "element_ref": {"type": ["string", "null"]},
                    "text": {"type": ["string", "null"]},
                    "key": {"type": ["string", "null"]},
                },
                "required": ["element_ref", "text", "key"],
                "additionalProperties": False,
            },
            "artifact": {
                "type": ["object", "null"],
                "properties": {
                    "kind": {"type": ["string", "null"]},
                    "label": {"type": ["string", "null"]},
                    "path": {"type": ["string", "null"]},
                },
                "required": ["kind", "label", "path"],
                "additionalProperties": False,
            },
            "snapshot": {
                "type": ["object", "null"],
                "properties": {
                    "interactive_elements": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "ref": {"type": "string"},
                                "tag": {"type": ["string", "null"]},
                                "text": {"type": ["string", "null"]},
                                "aria_label": {"type": ["string", "null"]},
                                "name": {"type": ["string", "null"]},
                                "id": {"type": ["string", "null"]},
                                "target_binding": {
                                    "type": ["object", "null"],
                                    "properties": {
                                        "binding_source": {"type": ["string", "null"]},
                                        "binding_session_id": {"type": ["string", "null"]},
                                        "binding_tab_id": {"type": ["string", "null"]},
                                        "binding_url": {"type": ["string", "null"]},
                                        "binding_dom_version": {"type": ["string", "null"]},
                                    },
                                    "required": [
                                        "binding_source",
                                        "binding_session_id",
                                        "binding_tab_id",
                                        "binding_url",
                                        "binding_dom_version",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "required": ["ref", "tag", "text", "aria_label", "name", "id", "target_binding"],
                            "additionalProperties": False,
                        },
                    },
                    "visible_text": {"type": ["string", "null"]},
                    "max_nodes": {"type": ["integer", "null"]},
                    "target_binding_context": {
                        "type": ["object", "null"],
                        "properties": {
                            "binding_source": {"type": ["string", "null"]},
                            "binding_session_id": {"type": ["string", "null"]},
                            "binding_tab_id": {"type": ["string", "null"]},
                            "binding_url": {"type": ["string", "null"]},
                            "binding_dom_version": {"type": ["string", "null"]},
                        },
                        "required": [
                            "binding_source",
                            "binding_session_id",
                            "binding_tab_id",
                            "binding_url",
                            "binding_dom_version",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": ["interactive_elements", "visible_text", "max_nodes", "target_binding_context"],
                "additionalProperties": False,
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "contract_version": {"type": "integer"},
                    "tool_family": {"type": "string"},
                    "platform_owned": {"type": "boolean"},
                    "runtime_boundary": {"type": "string"},
                    "execution_engine": {"type": "string"},
                },
                "required": [
                    "contract_version",
                    "tool_family",
                    "platform_owned",
                    "runtime_boundary",
                    "execution_engine",
                ],
                "additionalProperties": False,
            },
            "filename": {"type": ["string", "null"]},
            "file_path": {"type": ["string", "null"]},
            "download_url": {"type": ["string", "null"]},
            "download_markdown": {"type": ["string", "null"]},
        },
        "required": [
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
        ],
        "additionalProperties": False,
    }


def _build_not_implemented_payload(
    *,
    tool_name: str,
    operation: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "ok": False,
        "tool": tool_name,
        "operation": operation,
        "status": "not_implemented",
        "error_code": "browser_not_implemented",
        "message": "Browser builtin contract is wired, but the execution engine is intentionally not implemented in this phase.",
        "browser_context": {
            "session_id": args.get("session_id"),
            "tab_id": args.get("tab_id"),
            "url": args.get("url"),
            "page_title": None,
        },
        "target": {
            "element_ref": args.get("element_ref"),
            "text": args.get("text"),
            "key": args.get("key"),
        },
        "artifact": {
            "kind": "screenshot" if operation == "screenshot" else None,
            "label": args.get("label"),
            "path": None,
        },
        "snapshot": {
            "interactive_elements": None if operation != "snapshot" else [],
            "visible_text": None,
            "max_nodes": args.get("max_nodes"),
            "target_binding_context": None,
        },
        "filename": None,
        "file_path": None,
        "download_url": None,
        "download_markdown": None,
        "metadata": {
            "contract_version": BROWSER_CONTRACT_VERSION,
            "tool_family": BROWSER_TOOL_FAMILY,
            "platform_owned": True,
            "runtime_boundary": "builtin_tool_only",
            "execution_engine": "placeholder",
        },
    }


def _build_success_payload(
    *,
    tool_name: str,
    operation: str,
    args: Dict[str, Any],
    url: Optional[str],
    page_title: Optional[str],
    snapshot: Optional[Dict[str, Any]] = None,
    artifact: Optional[Dict[str, Any]] = None,
    artifact_download: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "tool": tool_name,
        "operation": operation,
        "status": "succeeded",
        "error_code": None,
        "message": "Browser operation completed through the Yue builtin browser tool boundary.",
        "browser_context": {
            "session_id": args.get("session_id"),
            "tab_id": args.get("tab_id"),
            "url": url,
            "page_title": page_title,
        },
        "target": {
            "element_ref": args.get("element_ref"),
            "text": args.get("text"),
            "key": args.get("key"),
        },
        "artifact": (
            {
                "kind": "screenshot" if operation == "screenshot" else None,
                "label": args.get("label"),
                "path": None,
            }
            if artifact is None
            else artifact
        ),
        "snapshot": {
            "interactive_elements": None,
            "visible_text": None,
            "max_nodes": args.get("max_nodes"),
            "target_binding_context": None,
        }
        if snapshot is None
        else snapshot,
        "filename": artifact_download.get("filename") if artifact_download else None,
        "file_path": artifact_download.get("file_path") if artifact_download else None,
        "download_url": artifact_download.get("download_url") if artifact_download else None,
        "download_markdown": artifact_download.get("download_markdown") if artifact_download else None,
        "metadata": {
            "contract_version": BROWSER_CONTRACT_VERSION,
            "tool_family": BROWSER_TOOL_FAMILY,
            "platform_owned": True,
            "runtime_boundary": "builtin_tool_only",
            "execution_engine": "playwright",
        },
    }


class BrowserBuiltinTool(BaseTool):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        operation: str,
        parameters: Dict[str, Any],
        recommended_approval_policy: str,
        runtime_metadata_expectations: Dict[str, Any],
        structured_failure_codes: Optional[list[str]] = None,
        continuity_contract: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name=name, description=description, parameters=parameters)
        self.operation = operation
        self.output_schema = _base_result_schema(operation)
        self.contract_metadata = {
            "contract_version": BROWSER_CONTRACT_VERSION,
            "tool_family": BROWSER_TOOL_FAMILY,
            "operation": operation,
            "recommended_approval_policy": recommended_approval_policy,
            "runtime_metadata_expectations": runtime_metadata_expectations,
            "platform_boundary": "builtin_tool_only",
            "execution_engine": "playwright" if operation in {"open", "snapshot", "click", "type", "press", "screenshot"} else "placeholder",
        }
        if structured_failure_codes:
            self.contract_metadata["structured_failure_codes"] = structured_failure_codes
        if continuity_contract:
            self.contract_metadata["continuity"] = continuity_contract

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        if self.operation == "open":
            return await self._execute_open(args if isinstance(args, dict) else {})
        if self.operation == "snapshot":
            return await self._execute_snapshot(args if isinstance(args, dict) else {})
        if self.operation == "click":
            return await self._execute_click(args if isinstance(args, dict) else {})
        if self.operation == "type":
            return await self._execute_type(args if isinstance(args, dict) else {})
        if self.operation == "press":
            return await self._execute_press(args if isinstance(args, dict) else {})
        if self.operation == "screenshot":
            return await self._execute_screenshot(args if isinstance(args, dict) else {})
        return json.dumps(
            _build_not_implemented_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args if isinstance(args, dict) else {},
            ),
            ensure_ascii=False,
            indent=2,
        )

    async def _execute_open(self, args: Dict[str, Any]) -> str:
        url = args.get("url")
        wait_until = args.get("wait_until")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url is required")
        if not isinstance(wait_until, str) or not wait_until.strip():
            wait_until = "load"
        _require_playwright_dependency(self.name)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url.strip(), wait_until=wait_until, timeout=30000)
                    final_url = page.url
                    page_title = await page.title()
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"browser_open timed out while loading {url}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"browser_open failed for {url}: {exc}") from exc

        return json.dumps(
            _build_success_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args,
                url=final_url,
                page_title=page_title,
            ),
            ensure_ascii=False,
            indent=2,
        )

    async def _execute_press(self, args: Dict[str, Any]) -> str:
        key = args.get("key")
        wait_until = args.get("wait_until")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key is required")
        url = _require_navigation_url(tool_name=self.name, args=args)
        if not isinstance(wait_until, str) or not wait_until.strip():
            wait_until = "load"
        _require_playwright_dependency(self.name)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url.strip(), wait_until=wait_until, timeout=30000)
                    await page.keyboard.press(key.strip())
                    final_url = page.url
                    page_title = await page.title()
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"browser_press timed out while loading {url}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"browser_press failed for {url}: {exc}") from exc

        return json.dumps(
            _build_success_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args,
                url=final_url,
                page_title=page_title,
            ),
            ensure_ascii=False,
            indent=2,
        )

    async def _execute_click(self, args: Dict[str, Any]) -> str:
        wait_until = args.get("wait_until")
        wait_after = bool(args.get("wait_after", True))
        binding_source = args.get("binding_source")
        node_index = _parse_minted_target_ref(args.get("element_ref"), binding_source)
        url = _require_navigation_url(tool_name=self.name, args=args, continuity_sensitive=True)
        if not isinstance(wait_until, str) or not wait_until.strip():
            wait_until = "load"
        _require_playwright_dependency(self.name)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url.strip(), wait_until=wait_until, timeout=30000)
                    click_result = await page.evaluate(
                        """({ selector, nodeIndex }) => {
                          const nodes = Array.from(document.querySelectorAll(selector));
                          const target = nodes[nodeIndex - 1];
                          if (!target) {
                            return { clicked: false, text: null };
                          }
                          const text = (target.innerText || target.textContent || "").replace(/\\s+/g, ' ').trim() || null;
                          target.click();
                          return { clicked: true, text };
                        }""",
                        {"selector": INTERACTIVE_SELECTOR, "nodeIndex": node_index},
                    )
                    if not isinstance(click_result, dict) or click_result.get("clicked") is not True:
                        raise RuntimeError(f"browser_click could not resolve minted target {args.get('element_ref')}")
                    if wait_after:
                        await page.wait_for_load_state("load", timeout=3000)
                    final_url = page.url
                    page_title = await page.title()
                    args = {
                        **args,
                        "text": click_result.get("text"),
                    }
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"browser_click timed out while loading {url}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"browser_click failed for {url}: {exc}") from exc

        return json.dumps(
            _build_success_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args,
                url=final_url,
                page_title=page_title,
            ),
            ensure_ascii=False,
            indent=2,
        )

    async def _execute_type(self, args: Dict[str, Any]) -> str:
        wait_until = args.get("wait_until")
        binding_source = args.get("binding_source")
        text = args.get("text")
        clear_first = bool(args.get("clear_first", False))
        node_index = _parse_minted_target_ref(args.get("element_ref"), binding_source)
        url = _require_navigation_url(tool_name=self.name, args=args, continuity_sensitive=True)
        if not isinstance(text, str):
            raise ValueError("text is required")
        if not isinstance(wait_until, str) or not wait_until.strip():
            wait_until = "load"
        _require_playwright_dependency(self.name)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url.strip(), wait_until=wait_until, timeout=30000)
                    type_result = await page.evaluate(
                        """({ selector, nodeIndex, text, clearFirst }) => {
                          const nodes = Array.from(document.querySelectorAll(selector));
                          const target = nodes[nodeIndex - 1];
                          if (!target) {
                            return { typed: false, tag: null };
                          }
                          const tag = target.tagName.toLowerCase();
                          const isFormField = tag === 'input' || tag === 'textarea' || tag === 'select';
                          if (!isFormField) {
                            return { typed: false, tag };
                          }
                          if (clearFirst && 'value' in target) {
                            target.value = '';
                          }
                          if ('value' in target) {
                            target.value = `${target.value ?? ''}${text}`;
                          }
                          target.dispatchEvent(new Event('input', { bubbles: true }));
                          target.dispatchEvent(new Event('change', { bubbles: true }));
                          return { typed: true, tag };
                        }""",
                        {
                            "selector": INTERACTIVE_SELECTOR,
                            "nodeIndex": node_index,
                            "text": text,
                            "clearFirst": clear_first,
                        },
                    )
                    if not isinstance(type_result, dict) or type_result.get("typed") is not True:
                        raise RuntimeError(f"browser_type could not resolve minted target {args.get('element_ref')}")
                    final_url = page.url
                    page_title = await page.title()
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"browser_type timed out while loading {url}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"browser_type failed for {url}: {exc}") from exc

        return json.dumps(
            _build_success_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args,
                url=final_url,
                page_title=page_title,
            ),
            ensure_ascii=False,
            indent=2,
        )

    async def _execute_screenshot(self, args: Dict[str, Any]) -> str:
        wait_until = args.get("wait_until")
        full_page = bool(args.get("full_page", False))
        label = args.get("label")
        url = _require_navigation_url(tool_name=self.name, args=args)
        if not isinstance(wait_until, str) or not wait_until.strip():
            wait_until = "load"
        _require_playwright_dependency(self.name)

        exports_dir = _resolve_exports_dir()
        fd, screenshot_path = tempfile.mkstemp(
            prefix="yue-browser-screenshot-",
            suffix=".png",
            dir=exports_dir,
        )
        os.close(fd)
        filename = os.path.basename(screenshot_path)
        download_url = f"/exports/{filename}"

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url.strip(), wait_until=wait_until, timeout=30000)
                    final_url = page.url
                    page_title = await page.title()
                    await page.screenshot(path=screenshot_path, full_page=full_page)
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"browser_screenshot timed out while loading {url}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"browser_screenshot failed for {url}: {exc}") from exc

        return json.dumps(
            _build_success_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args,
                url=final_url,
                page_title=page_title,
                artifact={
                    "kind": "screenshot",
                    "label": label if isinstance(label, str) and label.strip() else "browser-screenshot",
                    "path": screenshot_path,
                },
                artifact_download={
                    "filename": filename,
                    "file_path": screenshot_path,
                    "download_url": download_url,
                    "download_markdown": f"[{filename}]({download_url})",
                },
            ),
            ensure_ascii=False,
            indent=2,
        )

    async def _execute_snapshot(self, args: Dict[str, Any]) -> str:
        include_text = bool(args.get("include_text", True))
        include_interactive = bool(args.get("include_interactive_elements", True))
        max_nodes = args.get("max_nodes")
        wait_until = args.get("wait_until")
        url = _require_navigation_url(tool_name=self.name, args=args)
        if not isinstance(wait_until, str) or not wait_until.strip():
            wait_until = "load"
        if not isinstance(max_nodes, int) or max_nodes < 1:
            max_nodes = 50
        _require_playwright_dependency(self.name)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url.strip(), wait_until=wait_until, timeout=30000)
                    final_url = page.url
                    page_title = await page.title()
                    snapshot_payload = await page.evaluate(
                        """({ includeText, includeInteractive, maxNodes, bindingSource, bindingSessionId, bindingTabId, bindingUrl }) => {
                          const clampText = (value, maxLen = 4000) => {
                            if (!value) return null;
                            const normalized = String(value).replace(/\\s+/g, ' ').trim();
                            if (!normalized) return null;
                            return normalized.slice(0, maxLen);
                          };
                          const interactiveSelector = [
                            'a[href]',
                            'button',
                            'input',
                            'textarea',
                            'select',
                            '[role="button"]',
                            '[tabindex]'
                          ].join(',');
                          const interactiveElements = includeInteractive
                            ? Array.from(document.querySelectorAll(interactiveSelector))
                                .slice(0, maxNodes)
                                .map((el, index) => ({
                                  ref: `${bindingSource}#node:${index + 1}`,
                                  tag: el.tagName.toLowerCase(),
                                  text: clampText(el.innerText || el.textContent, 240),
                                  aria_label: clampText(el.getAttribute('aria-label'), 160),
                                  name: clampText(el.getAttribute('name'), 120),
                                  id: clampText(el.getAttribute('id'), 120),
                                  target_binding: {
                                    binding_source: bindingSource,
                                    binding_session_id: bindingSessionId,
                                    binding_tab_id: bindingTabId,
                                    binding_url: bindingUrl,
                                    binding_dom_version: null,
                                  },
                                }))
                            : null;
                          const visibleText = includeText
                            ? clampText(document.body ? (document.body.innerText || document.body.textContent) : '', 4000)
                            : null;
                          return {
                            interactive_elements: interactiveElements,
                            visible_text: visibleText,
                            max_nodes: maxNodes,
                            target_binding_context: {
                              binding_source: bindingSource,
                              binding_session_id: bindingSessionId,
                              binding_tab_id: bindingTabId,
                              binding_url: bindingUrl,
                              binding_dom_version: null,
                            },
                          };
                        }""",
                        {
                            "includeText": include_text,
                            "includeInteractive": include_interactive,
                            "maxNodes": max_nodes,
                            "bindingSource": f"snapshot:{self.name}",
                            "bindingSessionId": args.get("session_id"),
                            "bindingTabId": args.get("tab_id"),
                            "bindingUrl": final_url,
                        },
                    )
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"browser_snapshot timed out while loading {url}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"browser_snapshot failed for {url}: {exc}") from exc

        return json.dumps(
            _build_success_payload(
                tool_name=self.name,
                operation=self.operation,
                args=args,
                url=final_url,
                page_title=page_title,
                snapshot=snapshot_payload,
            ),
            ensure_ascii=False,
            indent=2,
        )


browser_tool_contracts = [
    BrowserBuiltinTool(
        name="browser_open",
        operation="open",
        description="Open a page in a Yue-managed browser session. This Phase 1 builtin defines the contract only and does not execute a real browser engine.",
        parameters={
            "type": "object",
            "properties": {
                **_common_browser_fields(),
                "url": {
                    "type": "string",
                    "description": "Absolute URL to open.",
                },
                "new_tab": {
                    "type": "boolean",
                    "description": "Open in a new tab when true.",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Navigation readiness hint.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        recommended_approval_policy="auto",
        runtime_metadata_expectations={
            "required": ["operation", "url"],
            "optional": ["session_id", "tab_id", "wait_until"],
        },
        continuity_contract={
            "contract_mode": "single_use_url_scoped",
            "authoritative_target_required": False,
            "resumable_continuity": "not_required",
        },
    ),
    BrowserBuiltinTool(
        name="browser_snapshot",
        operation="snapshot",
        description="Capture structured page evidence from a Yue-managed browser session. This Phase 1 builtin defines the contract only and does not execute a real browser engine.",
        parameters={
            "type": "object",
            "properties": {
                **_common_browser_fields(),
                "url": {
                    "type": "string",
                    "description": "URL for a single-use snapshot. Persistent browser session reuse is not implemented in this phase.",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Navigation readiness hint when url is provided.",
                },
                "include_text": {
                    "type": "boolean",
                    "description": "Include visible text summary when true.",
                },
                "include_interactive_elements": {
                    "type": "boolean",
                    "description": "Include clickable or typable elements when true.",
                },
                "max_nodes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum number of snapshot nodes to return.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        recommended_approval_policy="auto",
        runtime_metadata_expectations={
            "required": ["operation", "url"],
            "optional": ["session_id", "tab_id", "url", "wait_until", "max_nodes", "binding_source", "binding_session_id", "binding_tab_id", "binding_url", "binding_dom_version"],
        },
        continuity_contract={
            "contract_mode": "single_use_url_scoped",
            "authoritative_target_required": False,
            "resumable_continuity": "target_minting_only",
        },
    ),
    BrowserBuiltinTool(
        name="browser_click",
        operation="click",
        description="Click a referenced element in a Yue-managed browser session. When no persistent session is available, this builtin can replay a single-use URL-scoped click against a platform-minted target reference.",
        parameters={
            "type": "object",
            "properties": {
                **_common_browser_fields(),
                **_target_binding_fields(),
                "url": {
                    "type": "string",
                    "description": "Optional URL for a single-use click when no persistent browser session is available.",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Navigation readiness hint when url is provided.",
                },
                "element_ref": {
                    "type": "string",
                    "description": "Stable element reference resolved from a prior snapshot.",
                },
                "wait_after": {
                    "type": "boolean",
                    "description": "Wait for follow-up navigation or UI work when true.",
                },
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        recommended_approval_policy="manual",
        runtime_metadata_expectations={
            "required": ["operation", "element_ref"],
            "optional": ["session_id", "tab_id", "url", "binding_source", "binding_session_id", "binding_tab_id", "binding_url", "binding_dom_version", "active_dom_version"],
        },
        structured_failure_codes=[
            "browser_session_required",
            "browser_tab_required",
            "browser_target_required",
            "browser_target_stale",
            "browser_target_context_mismatch",
        ],
        continuity_contract={
            "contract_mode": "authoritative_target_mutation",
            "authoritative_target_required": True,
            "resumable_continuity": "deferred",
            "current_execution_mode": "single_use_url_scoped",
        },
    ),
    BrowserBuiltinTool(
        name="browser_type",
        operation="type",
        description="Type text into a referenced element in a Yue-managed browser session. When no persistent session is available, this builtin can replay a single-use URL-scoped type action against a platform-minted target reference.",
        parameters={
            "type": "object",
            "properties": {
                **_common_browser_fields(),
                **_target_binding_fields(),
                "url": {
                    "type": "string",
                    "description": "Optional URL for a single-use type action when no persistent browser session is available.",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Navigation readiness hint when url is provided.",
                },
                "element_ref": {
                    "type": "string",
                    "description": "Stable element reference resolved from a prior snapshot.",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type into the target field.",
                },
                "clear_first": {
                    "type": "boolean",
                    "description": "Clear current field value before typing when true.",
                },
            },
            "required": ["element_ref", "text"],
            "additionalProperties": False,
        },
        recommended_approval_policy="manual",
        runtime_metadata_expectations={
            "required": ["operation", "element_ref"],
            "optional": ["session_id", "tab_id", "url", "wait_until", "text", "binding_source", "binding_session_id", "binding_tab_id", "binding_url", "binding_dom_version", "active_dom_version"],
        },
        structured_failure_codes=[
            "browser_session_required",
            "browser_tab_required",
            "browser_target_required",
            "browser_target_stale",
            "browser_target_context_mismatch",
        ],
        continuity_contract={
            "contract_mode": "authoritative_target_mutation",
            "authoritative_target_required": True,
            "resumable_continuity": "deferred",
            "current_execution_mode": "single_use_url_scoped",
        },
    ),
    BrowserBuiltinTool(
        name="browser_press",
        operation="press",
        description="Send a key press to a Yue-managed browser session. When no persistent session is available, this builtin can open a single-use URL and send a page-level key press.",
        parameters={
            "type": "object",
            "properties": {
                **_common_browser_fields(),
                "url": {
                    "type": "string",
                    "description": "URL for a single-use page-level key press. Persistent browser session reuse is not implemented in this phase.",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Navigation readiness hint when url is provided.",
                },
                "element_ref": {
                    "type": "string",
                    "description": "Optional element reference that should receive the key event.",
                },
                "key": {
                    "type": "string",
                    "description": "Keyboard key to press, such as Enter or Escape.",
                },
            },
            "required": ["url", "key"],
            "additionalProperties": False,
        },
        recommended_approval_policy="manual",
        runtime_metadata_expectations={
            "required": ["operation", "url", "key"],
            "optional": ["session_id", "tab_id", "url", "wait_until", "element_ref"],
        },
        continuity_contract={
            "contract_mode": "single_use_url_scoped_mutation",
            "authoritative_target_required": False,
            "resumable_continuity": "not_required",
        },
    ),
    BrowserBuiltinTool(
        name="browser_screenshot",
        operation="screenshot",
        description="Capture a screenshot from a Yue-managed browser session. This Phase 1 builtin defines the contract only and does not execute a real browser engine.",
        parameters={
            "type": "object",
            "properties": {
                **_common_browser_fields(),
                "url": {
                    "type": "string",
                    "description": "URL for a single-use screenshot. Persistent browser session reuse is not implemented in this phase.",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "Navigation readiness hint when url is provided.",
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture a full-page image when true.",
                },
                "label": {
                    "type": "string",
                    "description": "Optional label for the screenshot artifact.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        recommended_approval_policy="auto",
        runtime_metadata_expectations={
            "required": ["operation", "url"],
            "optional": ["session_id", "tab_id", "url", "wait_until", "label"],
        },
        continuity_contract={
            "contract_mode": "single_use_url_scoped",
            "authoritative_target_required": False,
            "resumable_continuity": "not_required",
        },
    ),
]


for browser_tool in browser_tool_contracts:
    builtin_tool_registry.register(browser_tool)
