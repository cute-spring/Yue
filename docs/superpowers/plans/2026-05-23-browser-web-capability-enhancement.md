# Browser / Web Capability Enhancement Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the browser/web capability gap by adding a lightweight `builtin:web_fetch` tool for public internet content retrieval, a Playwright MCP template for full browser automation (including enterprise intranet form filling and submission), and wiring web capabilities (`CAP_WEB_FETCH` / `CAP_WEB_SEARCH` / `CAP_BROWSER_AUTOMATION`) into model routing — giving Yue agents first-class web browsing without requiring users to manually configure MCP servers for basic fetch tasks, and enabling intelligent intranet form automation driven by natural language prompts.

**Architecture:** Follow existing patterns: `builtin:web_fetch` mirrors `builtin/docs.py` and `builtin/system.py` patterns (a `BaseTool` subclass registered with `builtin_tool_registry`). A shared `_web_guards` module (separate file `_web_guards.py`) handles SSRF protection (IP checks, DNS resolution guard, redirect validation) and content truncation, reused by `web_fetch` and future web tools. A new Playwright MCP template follows the `DEFAULT_TEMPLATES` pattern in `templates.py`. New capability constants (`CAP_WEB_FETCH`, `CAP_WEB_SEARCH`, `CAP_BROWSER_AUTOMATION`) are introduced to semantically distinguish URL retrieval from web search and browser automation, wire into tool detection, and feed model routing.

**Important design note — two tools, two domains:** `builtin:web_fetch` is purpose-built for **public internet** content retrieval only — its SSRF protection actively blocks all private/internal IPs, loopback, and link-local addresses. For **enterprise intranet** scenarios (internal web systems, form filling, authenticated pages), the Playwright MCP template is the correct tool — Playwright runs a local browser session that can reach any network the host machine can access, including corporate intranets.

**Tech Stack:** FastAPI, Pydantic, `httpx` (already installed), existing `BaseTool` / `BuiltinToolRegistry`, existing `config_service`, existing `templates.py`, pytest, Vitest.

---

## Background: Current State (2026-05-23)

Yue has **zero built-in web browsing tools**. The `CAP_WEB_SEARCH` constant exists in `capabilities.py` but is orphaned — no tool declares web search capability and nothing triggers it. The roadmap (Phase 4) lists "Web Search Connector (Tavily/DuckDuckGo integration)" as planned but with no implementation started.

The MCP infrastructure is mature and could accept a Playwright MCP server, but there is no template to ease configuration. The `httpx` library is already in `pyproject.toml` / `requirements.txt`, making a lightweight fetch tool low-effort.

### Existing tool inventory

| Tool ID | Name | Type |
|:--|:--|:--|
| `builtin:exec` | ExecTool | Builtin |
| `builtin:docs_list` | DocsListTool | Builtin |
| `builtin:docs_search` | DocsSearchTool | Builtin |
| `builtin:docs_read` | DocsReadTool | Builtin |
| `builtin:docs_inspect` | DocsInspectTool | Builtin |
| `builtin:get_current_time` | GetCurrentTimeTool | Builtin |
| `builtin:ppt_generate` | PptGenerateTool | Builtin |
| `builtin:excel_read` | ExcelReadTool | Builtin |
| `builtin:excel_query` | ExcelQueryTool | Builtin |
| `builtin:excel_inspect` | ExcelInspectTool | Builtin |

### Existing MCP templates

| ID | Name | Deployment |
|:--|:--|:--|
| `jira-company` | Jira MCP | mixed |
| `confluence-company` | Confluence MCP | mixed |
| `custom-company-mcp` | Custom Company MCP | custom_mcp |

---

## 1. Scope Locks

- **Priority 1 (this plan)**: `builtin:web_fetch` — single-URL fetch with `httpx`, strong SSRF guards (DNS resolution, redirect validation, broad IP blocking), content-type allowlist, byte-size cap, structured JSON response envelope. This covers the common case where the agent already has a public URL and needs lightweight text extraction from a static page. **Explicitly not for intranet/internal URLs** — SSRF protection blocks all private IPs, loopback, and link-local addresses.
- **Priority 2 (this plan)**: Playwright MCP template in `templates.py` — zero-code path for full browser control. Supports **public web** (navigate, click, fill, screenshot, JS-rendered pages) and **enterprise intranet** (internal web systems, form filling, authenticated pages, SSO flows). Playwright runs a local browser that reaches any network the host machine can access.
- **Priority 3 (this plan)**: Capability model — introduce `CAP_WEB_FETCH`, `CAP_WEB_SEARCH`, and `CAP_BROWSER_AUTOMATION` constants; wire web-fetch tool detection into model routing.
- **Priority 4 (this plan)**: Shared `_web_guards` module — SSRF protection (IP blocking, DNS resolution guard, redirect validation), protocol whitelist, content type allowlist, byte-size cap, content truncation, observability helpers. Reused by `web_fetch` and future `web_search`.
- **Deferred to follow-up plan**: `builtin:web_search` (multi-URL search via Brave/Tavily API), Playwright MCP deeper integration (preflighting, health checks, "intranet form assistant" Agent preset with optimized system prompt for form-filling workflows), domain allow/deny lists, JS-rendered page fetching, login-required pages, form interaction, anti-bot handling, PDF extraction.

### Enterprise Intranet Form Automation — Use Case & Requirements

A key intended use case for the Playwright MCP template is **enterprise intranet form automation**: Agent receives a natural language prompt (e.g., "Go to http://erp.internal.company.com/expense, fill in today's taxi receipt and submit") and autonomously executes the workflow.

**How it works with this plan (after deployment):**

1. User configures Playwright MCP server via the template in Yue UI (one-click)
2. User creates an Agent and enables the Playwright tools (`browser_navigate`, `browser_click`, `browser_fill`, `browser_snapshot`, etc.)
3. In chat, the user gives a natural language instruction targeting an intranet URL
4. The Agent's model decomposes the instruction into Playwright tool calls: `browser_navigate` → `browser_snapshot` (inspect page structure) → `browser_fill` (set form fields by element selector or label) → `browser_click` (submit button)
5. Results are returned in chat with optional screenshots for verification

**Prerequisites for intranet use (not automated by this plan):**
- Yue backend / Playwright runtime must be deployed on a machine with network access to the target intranet
- The browser session may need manual authentication (SSO login) on first use; subsequent requests share the session
- The underlying LLM model must have sufficient multi-step reasoning and tool-calling ability

---

## 2. File Map

### Backend

- Create: `backend/app/mcp/builtin/_web_guards.py` — SSRF validation, DNS resolution, IP blocking, content truncation, observability helpers
- Create: `backend/app/mcp/builtin/web.py` — WebFetchTool class (imports guards from `_web_guards.py`)
- Modify: `backend/app/mcp/builtin/__init__.py` — import web module so tool auto-registers
- Modify: `backend/app/mcp/templates.py` — add `playwright-mcp-browser` template
- Modify: `backend/app/services/llm/capabilities.py` — add `CAP_WEB_FETCH` / `CAP_WEB_SEARCH` / `CAP_BROWSER_AUTOMATION` constants and `detect_capabilities_from_tools` helper
- Test: `backend/tests/test_web_guards_unit.py` — unit tests for SSRF, DNS resolution, IPv6, metadata endpoints, redirect validation
- Test: `backend/tests/test_web_fetch_unit.py` — unit tests for WebFetchTool (JSON envelope, content-type, truncation, timeouts, validation)
- Test: `backend/tests/test_api_mcp_unit.py` — verify Playwright MCP template renders correctly
- Test: `backend/tests/test_capabilities_unit.py` — verify capability detection from tool lists
- Test: `backend/tests/test_tool_registry_integration.py` — verify web_fetch appears in registry

### Frontend

- (No frontend changes in this plan — `web_fetch` appears in existing tool lists automatically)
- **Manual QA verification required**: Enable `web_fetch` in an Agent from UI, ask it to fetch `https://example.com`, verify response is shown and execution trace is readable. Verify tool picker displays description correctly, `max_chars` appears as optional, tool ID persists as `builtin:web_fetch`.

---

## Chunk 1: Shared Web Guardrails Module

### Task 1: Create `_web_guards.py` with strong SSRF protection and observability

**Files:**
- Create: `backend/app/mcp/builtin/_web_guards.py`
- Create: `backend/tests/test_web_guards_unit.py`

**Design decisions:**
- **Protocol whitelist**: only `http://` and `https://` allowed (prevents `file://`, `ftp://`, `gopher://` SSRF)
- **IP blocking**: Use Python's built-in properties (`is_private`, `is_loopback`, `is_link_local`, `is_multicast`, `is_reserved`, `is_unspecified`) plus explicit network blocks (`0.0.0.0/8`, `100.64.0.0/10`, `224.0.0.0/4`, `240.0.0.0/4`, `255.255.255.255/32`, `::/128`, `::ffff:0:0/96`, `2001:db8::/32`) and explicit metadata endpoint blocking (`169.254.169.254`, `metadata.google.internal`)
- **DNS resolution guard**: Resolve hostnames with `socket.getaddrinfo` before fetching; reject if any resolved address is blocked
- **Redirect validation**: Default to `follow_redirects=False`; manually follow up to 3 redirects validating each target's URL and resolved IPs
- **Content-type allowlist**: `text/html`, `text/plain`, `application/json`, `application/xml`, `text/xml`, `text/markdown`
- **Byte cap**: Max 1 MB download size (checked via `Content-Length` header or streaming read)
- **Observability**: Log structured info (`host`, `status_code`, `content_type`, `elapsed_ms`, `truncated`, `error_code`, `final_url_host`) — never log full URL query params, response body, cookies, or auth headers
- **Content truncation**: default `max_chars=8000`, configurable range `[500, 50000]`
- **URL length limit**: max 4096 characters
- **Error protocol**: Consistent JSON envelope with `ok`, `error_code`, `message`, `hint`

- [ ] **Step 1: Write the guardrail tests**

```python
# backend/tests/test_web_guards_unit.py
import pytest
import ipaddress
from app.mcp.builtin._web_guards import (
    _validate_url,
    _is_blocked_ip,
    _resolve_hostname,
    _is_content_type_allowed,
    _validate_max_chars,
    _strip_html,
    _safe_url_for_logs,
    ALLOWED_CONTENT_TYPES,
    MIN_MAX_CHARS,
    MAX_MAX_CHARS,
    MAX_URL_LENGTH,
    MAX_BYTES,
)


class TestIPBlocking:
    """Tests for _is_blocked_ip covering all expected blocked ranges."""

    def test_blocks_loopback_ipv4(self):
        assert _is_blocked_ip(ipaddress.ip_address("127.0.0.1")) is True
        assert _is_blocked_ip(ipaddress.ip_address("127.255.255.255")) is True

    def test_blocks_loopback_ipv6(self):
        assert _is_blocked_ip(ipaddress.ip_address("::1")) is True

    def test_blocks_private_10_range(self):
        assert _is_blocked_ip(ipaddress.ip_address("10.0.0.1")) is True
        assert _is_blocked_ip(ipaddress.ip_address("10.255.255.255")) is True

    def test_blocks_private_172_range(self):
        assert _is_blocked_ip(ipaddress.ip_address("172.16.0.1")) is True
        assert _is_blocked_ip(ipaddress.ip_address("172.31.255.255")) is True

    def test_blocks_private_192_168_range(self):
        assert _is_blocked_ip(ipaddress.ip_address("192.168.0.1")) is True
        assert _is_blocked_ip(ipaddress.ip_address("192.168.255.255")) is True

    def test_blocks_link_local(self):
        assert _is_blocked_ip(ipaddress.ip_address("169.254.1.1")) is True
        assert _is_blocked_ip(ipaddress.ip_address("fe80::1")) is True

    def test_blocks_multicast(self):
        assert _is_blocked_ip(ipaddress.ip_address("224.0.0.1")) is True
        assert _is_blocked_ip(ipaddress.ip_address("ff00::1")) is True

    def test_blocks_reserved(self):
        assert _is_blocked_ip(ipaddress.ip_address("240.0.0.1")) is True

    def test_blocks_unspecified(self):
        assert _is_blocked_ip(ipaddress.ip_address("0.0.0.0")) is True
        assert _is_blocked_ip(ipaddress.ip_address("::")) is True

    def test_blocks_cgnat_100_64(self):
        assert _is_blocked_ip(ipaddress.ip_address("100.64.0.1")) is True

    def test_blocks_broadcast(self):
        assert _is_blocked_ip(ipaddress.ip_address("255.255.255.255")) is True

    def test_blocks_ipv4_mapped_ipv6(self):
        assert _is_blocked_ip(ipaddress.ip_address("::ffff:127.0.0.1")) is True

    def test_blocks_documentation_ipv6(self):
        assert _is_blocked_ip(ipaddress.ip_address("2001:db8::1")) is True

    def test_allows_public_ipv4(self):
        assert _is_blocked_ip(ipaddress.ip_address("8.8.8.8")) is False
        assert _is_blocked_ip(ipaddress.ip_address("93.184.216.34")) is False

    def test_allows_public_ipv6(self):
        assert _is_blocked_ip(ipaddress.ip_address("2606:2800:220:1:248:1893:25c8:1946")) is False


class TestURLValidation:
    """Tests for _validate_url with IP-based and scheme-based checks."""

    def test_allows_https_url(self):
        assert _validate_url("https://example.com/page") is None

    def test_allows_public_ip(self):
        assert _validate_url("http://93.184.216.34") is None

    def test_rejects_file_protocol(self):
        result = _validate_url("file:///etc/passwd")
        assert result is not None
        assert '"ok": false' in result
        assert "unsupported_protocol" in result

    def test_rejects_ftp_protocol(self):
        result = _validate_url("ftp://example.com/file")
        assert result is not None
        assert "unsupported_protocol" in result

    def test_rejects_loopback_ipv4(self):
        result = _validate_url("http://127.0.0.1:8080/admin")
        assert result is not None
        assert "private_ip_blocked" in result

    def test_rejects_loopback_ipv6(self):
        result = _validate_url("http://[::1]:8080/admin")
        assert result is not None
        assert "private_ip_blocked" in result

    def test_rejects_private_ip_10(self):
        result = _validate_url("http://10.0.0.1/api")
        assert result is not None
        assert "private_ip_blocked" in result

    def test_rejects_private_ip_192_168(self):
        result = _validate_url("http://192.168.1.1/admin")
        assert result is not None
        assert "private_ip_blocked" in result

    def test_rejects_metadata_aws(self):
        result = _validate_url("http://169.254.169.254/latest/meta-data/")
        assert result is not None
        assert "private_ip_blocked" in result

    def test_rejects_zero_ip(self):
        result = _validate_url("http://0.0.0.0/test")
        assert result is not None
        assert "private_ip_blocked" in result

    def test_rejects_no_hostname(self):
        result = _validate_url("http:///path")
        assert result is not None
        assert "invalid_url" in result

    def test_rejects_empty_url(self):
        result = _validate_url("")
        assert result is not None


class TestHostnameResolution:
    """Tests for _resolve_hostname and hostname-based SSRF blocking."""

    def test_resolves_public_hostname(self):
        addrs = _resolve_hostname("example.com")
        assert len(addrs) > 0
        for addr in addrs:
            assert not _is_blocked_ip(addr)

    @pytest.mark.parametrize("hostname", [
        "localhost",
        "metadata.google.internal",
    ])
    def test_blocks_private_hostnames(self, hostname, monkeypatch):
        """Simulate a hostname that resolves to a blocked IP."""
        import socket
        def mock_getaddrinfo(host, port):
            if host == "localhost":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
            elif host == "metadata.google.internal":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0))]
            return []
        monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)
        addrs = _resolve_hostname(hostname)
        assert len(addrs) > 0
        for addr in addrs:
            assert _is_blocked_ip(addr) is True


class TestContentTypeAllowlist:
    """Tests for _is_content_type_allowed."""

    def test_allows_text_html(self):
        assert _is_content_type_allowed("text/html") is True
        assert _is_content_type_allowed("text/html; charset=utf-8") is True

    def test_allows_text_plain(self):
        assert _is_content_type_allowed("text/plain") is True

    def test_allows_application_json(self):
        assert _is_content_type_allowed("application/json") is True

    def test_allows_text_markdown(self):
        assert _is_content_type_allowed("text/markdown") is True

    def test_rejects_pdf(self):
        assert _is_content_type_allowed("application/pdf") is False

    def test_rejects_image(self):
        assert _is_content_type_allowed("image/png") is False

    def test_rejects_zip(self):
        assert _is_content_type_allowed("application/zip") is False

    def test_rejects_video(self):
        assert _is_content_type_allowed("video/mp4") is False

    def test_rejects_octet_stream(self):
        assert _is_content_type_allowed("application/octet-stream") is False


class TestMaxCharsValidation:
    """Tests for _validate_max_chars."""

    def test_default_passes(self):
        assert _validate_max_chars(8000) == 8000

    def test_below_min_clamped(self):
        assert _validate_max_chars(100) == MIN_MAX_CHARS

    def test_above_max_clamped(self):
        assert _validate_max_chars(999999) == MAX_MAX_CHARS

    def test_zero_clamped(self):
        assert _validate_max_chars(0) == MIN_MAX_CHARS

    def test_negative_clamped(self):
        assert _validate_max_chars(-100) == MIN_MAX_CHARS

    def test_none_uses_default(self):
        assert _validate_max_chars(None) == 8000

    def test_string_converted(self):
        assert _validate_max_chars("3000") == 3000

    def test_invalid_string_clamped(self):
        assert _validate_max_chars("abc") == 8000


class TestHTMLStripping:
    """Tests for _strip_html."""

    def test_strips_tags(self):
        assert _strip_html("<p>Hello</p>") == "Hello"

    def test_strips_script_and_style(self):
        html = "<html><head><style>body{}</style><script>alert(1)</script></head><body><p>Content</p></body></html>"
        result = _strip_html(html)
        assert "Content" in result
        assert "alert(1)" not in result
        assert "body{}" not in result

    def test_decodes_html_entities(self):
        assert _strip_html("&amp; &lt; &gt; &quot;") == '& < > "'

    def test_collapses_whitespace(self):
        assert _strip_html("hello    world\n\ntest") == "hello world test"

    def test_extracts_title(self):
        title, body = _strip_html("<html><head><title>My Page</title></head><body><p>Hello</p></body></html>", extract_title=True)
        assert title == "My Page"
        assert "Hello" in body


class TestSafeURLLogging:
    """Tests for _safe_url_for_logs."""

    def test_strips_query_params(self):
        result = _safe_url_for_logs("https://example.com/path?api_key=secret&token=xyz")
        assert result == "https://example.com/path"
        assert "secret" not in result
        assert "token" not in result

    def test_truncates_long_path(self):
        long_path = "/" + "a" * 200
        result = _safe_url_for_logs(f"https://example.com{long_path}")
        assert len(result) <= 140  # scheme + host + 120 chars of path

    def test_preserves_hostname(self):
        result = _safe_url_for_logs("https://docs.example.com/ref/page.html?q=1")
        assert result.startswith("https://docs.example.com")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_web_guards_unit.py -v
```
Expected: FAIL (module/function not defined)

- [ ] **Step 3: Implement `_web_guards.py`**

```python
# backend/app/mcp/builtin/_web_guards.py
import html as html_module
import ipaddress
import json
import logging
import re
import socket
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 8000
DEFAULT_TIMEOUT_S = 15.0
MAX_REDIRECTS = 3
MAX_BYTES = 1_000_000
MAX_URL_LENGTH = 4096
MIN_MAX_CHARS = 500
MAX_MAX_CHARS = 50000

ALLOWED_SCHEMES = {"http", "https"}

ALLOWED_CONTENT_TYPES = {
    "text/html",
    "text/plain",
    "application/json",
    "application/xml",
    "text/xml",
    "text/markdown",
}

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r"<[^>]*>")
_WHITESPACE_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# Explicit metadata endpoints to block even if covered by IP ranges
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
}

# Additional network blocks beyond Python's built-in properties
_EXTRA_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::ffff:0:0/96"),
    ipaddress.ip_network("2001:db8::/32"),
]


def _is_blocked_ip(addr: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Check if an IP address should be blocked for SSRF protection.
    
    Uses Python's built-in properties plus extra network blocks for completeness.
    """
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    ):
        return True

    for net in _EXTRA_BLOCKED_NETWORKS:
        if addr in net:
            return True

    return False


def _resolve_hostname(hostname: str) -> List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """Resolve a hostname to IP addresses via DNS."""
    try:
        infos = socket.getaddrinfo(hostname, None)
        addrs: List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = []
        seen = set()
        for info in infos:
            ip_str = info[4][0]
            if ip_str not in seen:
                seen.add(ip_str)
                addrs.append(ipaddress.ip_address(ip_str))
        return addrs
    except socket.gaierror:
        logger.debug("DNS resolution failed for hostname: %s", hostname)
        return []


def _validate_url(url: str) -> Optional[str]:
    """Validate URL for safety at the URL-parsing layer.
    
    Checks scheme, hostname presence, IP literals.
    Does NOT perform DNS resolution (handled separately before fetch).
    
    Returns error JSON string or None if valid.
    """
    if not url or not isinstance(url, str):
        return json.dumps({
            "ok": False,
            "error_code": "invalid_url",
            "message": "URL is missing or empty.",
            "hint": "Provide a complete URL starting with http:// or https://.",
        }, ensure_ascii=False)

    if len(url) > MAX_URL_LENGTH:
        return json.dumps({
            "ok": False,
            "error_code": "url_too_long",
            "message": f"URL exceeds maximum length of {MAX_URL_LENGTH} characters.",
            "hint": "Shorten the URL or use a different resource.",
        }, ensure_ascii=False)

    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        return json.dumps({
            "ok": False,
            "error_code": "unsupported_protocol",
            "message": f"Protocol '{parsed.scheme}' is not allowed. Only http and https are supported.",
            "hint": "Use http:// or https:// URLs only.",
        }, ensure_ascii=False)

    hostname = parsed.hostname
    if not hostname:
        return json.dumps({
            "ok": False,
            "error_code": "invalid_url",
            "message": "URL has no valid hostname.",
            "hint": "Provide a complete URL with a hostname.",
        }, ensure_ascii=False)

    # Check if hostname is an explicit blocked hostname
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return json.dumps({
            "ok": False,
            "error_code": "blocked_hostname",
            "message": f"Hostname '{hostname}' is blocked for security.",
            "hint": "Only publicly accessible URLs are supported.",
        }, ensure_ascii=False)

    # Check if hostname is a literal IP address
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP literal — DNS resolution check happens before fetch
        return None

    if _is_blocked_ip(addr):
        return json.dumps({
            "ok": False,
            "error_code": "private_ip_blocked",
            "message": f"URL resolves to a private/internal IP address ({hostname}). This is blocked for security.",
            "hint": "Only publicly accessible URLs are supported.",
        }, ensure_ascii=False)

    return None


def _validate_hostname_resolution(hostname: str) -> Optional[str]:
    """Resolve hostname via DNS and check all resolved IPs are safe.
    
    Returns error JSON string if any resolved IP is blocked, or None if safe.
    """
    addrs = _resolve_hostname(hostname)
    if not addrs:
        return json.dumps({
            "ok": False,
            "error_code": "dns_resolution_failed",
            "message": f"Could not resolve hostname '{hostname}'.",
            "hint": "Verify the URL is correct and the domain exists.",
        }, ensure_ascii=False)

    for addr in addrs:
        if _is_blocked_ip(addr):
            return json.dumps({
                "ok": False,
                "error_code": "private_ip_blocked",
                "message": f"Hostname '{hostname}' resolves to a private/internal IP address ({addr}). This is blocked for security.",
                "hint": "Only publicly accessible URLs are supported.",
            }, ensure_ascii=False)

    return None


def _is_content_type_allowed(content_type: str) -> bool:
    """Check if the content-type is in the allowed list."""
    if not content_type:
        return False
    main_type = content_type.split(";")[0].strip().lower()
    return main_type in ALLOWED_CONTENT_TYPES


def _validate_max_chars(max_chars: Any) -> int:
    """Validate and clamp max_chars to the allowed range [MIN_MAX_CHARS, MAX_MAX_CHARS]."""
    try:
        value = int(max_chars)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CHARS
    if value <= 0:
        return DEFAULT_MAX_CHARS
    return max(MIN_MAX_CHARS, min(value, MAX_MAX_CHARS))


def _strip_html(raw: str, extract_title: bool = False) -> Union[str, Tuple[Optional[str], str]]:
    """Strip HTML tags, scripts, styles and return clean text.
    
    If extract_title is True, returns (title, body) tuple.
    """
    # Extract title before stripping
    title = None
    if extract_title:
        title_match = _TITLE_RE.search(raw)
        if title_match:
            title = html_module.unescape(title_match.group(1).strip())

    # Remove script, style, noscript blocks first
    text = _SCRIPT_STYLE_RE.sub(" ", raw)
    # Remove remaining HTML tags
    text = _HTML_TAG_RE.sub(" ", text)
    # Decode HTML entities
    text = html_module.unescape(text)
    # Collapse whitespace
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.strip()

    if extract_title:
        return (title, text)
    return text


def _truncate_content(content: str, max_chars: int) -> Tuple[str, bool]:
    """Truncate content to max_chars. Returns (content, was_truncated)."""
    limit = _validate_max_chars(max_chars)
    if len(content) <= limit:
        return content, False
    return content[:limit], True


def _safe_url_for_logs(url: str) -> str:
    """Return a safe version of a URL for logging (no query params, truncated path)."""
    try:
        parsed = urlparse(url)
        path = parsed.path[:120]
        return f"{parsed.scheme}://{parsed.hostname}{path}"
    except Exception:
        return "[invalid-url]"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_web_guards_unit.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/mcp/builtin/_web_guards.py backend/tests/test_web_guards_unit.py
git commit -m "feat: add shared web guardrails module with DNS resolution SSRF protection, content-type allowlist, byte caps, and observability helpers"
```

---

## Chunk 2: `builtin:web_fetch` Tool

### Task 2: Implement `WebFetchTool` and register it

**Files:**
- Create: `backend/app/mcp/builtin/web.py`
- Modify: `backend/app/mcp/builtin/__init__.py`
- Modify: `backend/tests/test_web_fetch_unit.py` (create new)

**Design decisions:**
- Tool name: `web_fetch`
- Tool ID: `builtin:web_fetch`
- Parameters: `url` (required string, max 4096 chars), `max_chars` (optional int, clamped to [500, 50000], default 8000)
- **Response contract**: Consistent JSON envelope for both success and error:
  - Success: `{"ok": true, "url": "...", "final_url": "...", "status_code": 200, "content_type": "text/html", "title": "...", "text": "...", "truncated": false, "char_count": 1256}`
  - Error: `{"ok": false, "error_code": "...", "message": "...", "hint": "..."}`
- Uses `httpx.AsyncClient` with `follow_redirects=False`; manually follows up to 3 redirects with URL + DNS validation at each step
- Content-type check before reading body; reject unsupported types
- Byte cap enforced via `Content-Length` header or streaming read with early abort
- HTML stripping: remove script/style/noscript blocks, strip tags, decode entities, extract `<title>`
- Structured observability logging on every fetch

- [ ] **Step 1: Write the WebFetchTool tests**

```python
# backend/tests/test_web_fetch_unit.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY


class TestWebFetchToolExecute:
    """Tests for WebFetchTool.execute() method."""

    @pytest.mark.asyncio
    async def test_fetch_basic_html(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>Test</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://example.com"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await tool.execute(MagicMock(), {"url": "https://example.com"})
            parsed = json.loads(result)

            assert parsed["ok"] is True
            assert parsed["title"] == "Test"
            assert "Hello" in parsed["text"]
            assert "World" in parsed["text"]
            assert parsed["status_code"] == 200
            assert parsed["content_type"] == "text/html"

    @pytest.mark.asyncio
    async def test_fetch_rejects_file_url(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()
        result = await tool.execute(MagicMock(), {"url": "file:///etc/passwd"})
        parsed = json.loads(result)
        assert parsed["ok"] is False
        assert parsed["error_code"] == "unsupported_protocol"

    @pytest.mark.asyncio
    async def test_fetch_truncates_long_content(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>" + ("x" * 20000) + "</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://example.com"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await tool.execute(MagicMock(), {"url": "https://example.com", "max_chars": 1000})
            parsed = json.loads(result)

            assert parsed["ok"] is True
            assert parsed["truncated"] is True
            assert parsed["char_count"] == 1000
            assert len(parsed["text"]) == 1000

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        import httpx
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404)
            )

            result = await tool.execute(MagicMock(), {"url": "https://example.com/404"})
            parsed = json.loads(result)

            assert parsed["ok"] is False
            assert "404" in parsed.get("message", "")

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        import httpx
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")

            result = await tool.execute(MagicMock(), {"url": "https://slow.example.com"})
            parsed = json.loads(result)

            assert parsed["ok"] is False
            assert parsed["error_code"] == "timeout"

    @pytest.mark.asyncio
    async def test_fetch_rejects_pdf_content_type(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf", "content-length": "50000"}
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://example.com/doc.pdf"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await tool.execute(MagicMock(), {"url": "https://example.com/doc.pdf"})
            parsed = json.loads(result)

            assert parsed["ok"] is False
            assert parsed["error_code"] == "unsupported_content_type"

    @pytest.mark.asyncio
    async def test_fetch_rejects_oversized_response(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html", "content-length": "5000000"}
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://example.com/huge"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await tool.execute(MagicMock(), {"url": "https://example.com/huge"})
            parsed = json.loads(result)

            assert parsed["ok"] is False
            assert "too_large" in parsed.get("error_code", "")

    @pytest.mark.asyncio
    async def test_fetch_rejects_missing_url(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()
        result = await tool.execute(MagicMock(), {})
        parsed = json.loads(result)
        assert parsed["ok"] is False
        assert parsed["error_code"] == "invalid_arguments"

    @pytest.mark.asyncio
    async def test_fetch_rejects_empty_url(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()
        result = await tool.execute(MagicMock(), {"url": ""})
        parsed = json.loads(result)
        assert parsed["ok"] is False
        assert parsed["error_code"] == "invalid_url"

    @pytest.mark.asyncio
    async def test_fetch_rejects_localhost_hostname(self):
        """Verify that localhost (DNS-resolved) is blocked."""
        from app.mcp.builtin.web import WebFetchTool
        import socket

        tool = WebFetchTool()

        def mock_getaddrinfo(host, port):
            if host == "localhost":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
            return []

        with patch("socket.getaddrinfo", mock_getaddrinfo):
            result = await tool.execute(MagicMock(), {"url": "http://localhost:8080/test"})
            parsed = json.loads(result)
            assert parsed["ok"] is False
            assert "blocked" in parsed.get("error_code", "").lower() or "private" in parsed.get("error_code", "").lower()

    @pytest.mark.asyncio
    async def test_fetch_clamps_max_chars(self):
        from app.mcp.builtin.web import WebFetchTool
        tool = WebFetchTool()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>" + ("x" * 2000) + "</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://example.com"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            # max_chars below minimum should be clamped to MIN_MAX_CHARS (500)
            result = await tool.execute(MagicMock(), {"url": "https://example.com", "max_chars": 10})
            parsed = json.loads(result)

            assert parsed["ok"] is True
            assert parsed["char_count"] >= 500


class TestWebFetchToolRegistry:
    """Tests verifying the tool is registered and visible."""

    def test_tool_registered_in_registry(self):
        from app.mcp.builtin import builtin_tool_registry
        tool = builtin_tool_registry.get_tool("web_fetch")
        assert tool is not None
        assert tool.name == "web_fetch"

    def test_tool_metadata_format(self):
        from app.mcp.builtin import builtin_tool_registry
        meta = builtin_tool_registry.get_all_metadata()
        web_fetch_meta = next(m for m in meta if m["name"] == "web_fetch")
        assert web_fetch_meta["id"] == "builtin:web_fetch"
        assert web_fetch_meta["server"] == "builtin"
        assert "input_schema" in web_fetch_meta
        assert "url" in web_fetch_meta["input_schema"].get("required", [])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_web_fetch_unit.py -v
```
Expected: FAIL (WebFetchTool not defined)

- [ ] **Step 3: Create `web.py` with `WebFetchTool` class**

```python
# backend/app/mcp/builtin/web.py
import json
import logging
import time
from typing import Any, Dict

import httpx
from pydantic_ai import RunContext

from ._web_guards import (
    DEFAULT_MAX_CHARS,
    DEFAULT_TIMEOUT_S,
    MAX_BYTES,
    MAX_REDIRECTS,
    _validate_url,
    _validate_hostname_resolution,
    _is_content_type_allowed,
    _validate_max_chars,
    _strip_html,
    _truncate_content,
    _safe_url_for_logs,
)
from ..base import BaseTool
from .registry import builtin_tool_registry

logger = logging.getLogger(__name__)

WEB_FETCH_CONFIG = {
    "enabled": True,
    "timeout_seconds": DEFAULT_TIMEOUT_S,
    "max_chars_default": DEFAULT_MAX_CHARS,
    "max_chars_limit": 50000,
    "max_bytes": MAX_BYTES,
    "allow_redirects": False,
    "user_agent": "Yue/1.0 WebFetch",
}


def _build_error_response(error_code: str, message: str, hint: str = "") -> str:
    return json.dumps({
        "ok": False,
        "error_code": error_code,
        "message": message,
        "hint": hint,
    }, ensure_ascii=False)


def _build_success_response(
    url: str,
    final_url: str,
    status_code: int,
    content_type: str,
    text: str,
    char_count: int,
    truncated: bool,
    title: str = "",
) -> str:
    return json.dumps({
        "ok": True,
        "url": url,
        "final_url": final_url,
        "status_code": status_code,
        "content_type": content_type,
        "title": title,
        "text": text,
        "char_count": char_count,
        "truncated": truncated,
    }, ensure_ascii=False)


class WebFetchTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="web_fetch",
            description=(
                "Fetch content from a single URL and return cleaned text with metadata. "
                "Only http/https URLs to public addresses are allowed. "
                "Returns a structured JSON response with page title, text content, "
                "truncation status, and content type. "
                "Use this for reading documentation pages, blog posts, or any publicly accessible web content. "
                "For JavaScript-rendered pages or browser interaction, use a Playwright MCP server instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch. Must start with http:// or https://."
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to return (range 500-50000). Default 8000. Use lower values for quick scanning."
                    }
                },
                "required": ["url"]
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        url = args.get("url")
        if not url or not isinstance(url, str) or not url.strip():
            return _build_error_response(
                "invalid_arguments",
                "The 'url' parameter is required and must be a non-empty string.",
                "Provide a valid http:// or https:// URL.",
            )

        url = url.strip()
        max_chars = _validate_max_chars(args.get("max_chars"))

        t_start = time.monotonic()

        # 1. Validate URL at parse level
        error = _validate_url(url)
        if error:
            return error

        # 2. DNS resolution guard
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname
        if hostname:
            error = _validate_hostname_resolution(hostname)
            if error:
                return error

        # 3. Fetch with redirect validation
        current_url = url
        try:
            async with httpx.AsyncClient(
                timeout=WEB_FETCH_CONFIG["timeout_seconds"],
                follow_redirects=False,
                headers={"User-Agent": WEB_FETCH_CONFIG["user_agent"]},
            ) as client:
                redirect_count = 0
                while redirect_count <= MAX_REDIRECTS:
                    # Check Content-Length before fetching if available
                    head_response = await client.head(current_url)
                    content_length = head_response.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > WEB_FETCH_CONFIG["max_bytes"]:
                                elapsed = time.monotonic() - t_start
                                logger.info(
                                    "web_fetch blocked: size=%s bytes, host=%s, elapsed=%.0fms",
                                    content_length, _safe_url_for_logs(current_url), elapsed * 1000,
                                )
                                return _build_error_response(
                                    "response_too_large",
                                    f"Response size ({content_length} bytes) exceeds the maximum allowed ({WEB_FETCH_CONFIG['max_bytes']} bytes).",
                                    "Try a smaller resource or use a different tool.",
                                )
                        except ValueError:
                            pass  # Content-Length not parseable, proceed

                    response = await client.get(current_url)
                    response.raise_for_status()

                    # Handle redirect
                    if response.status_code in (301, 302, 303, 307, 308):
                        next_url = response.headers.get("location", "")
                        if not next_url:
                            break
                        # Resolve relative redirects
                        from urllib.parse import urljoin
                        current_url = urljoin(current_url, next_url)
                        # Validate redirect target
                        error = _validate_url(current_url)
                        if error:
                            return error
                        redirect_hostname = urlparse(current_url).hostname
                        if redirect_hostname:
                            error = _validate_hostname_resolution(redirect_hostname)
                            if error:
                                return error
                        redirect_count += 1
                        continue

                    # Not a redirect — process response
                    content_type = response.headers.get("content-type", "").lower()
                    final_url = str(response.url)

                    # Check content type
                    if not _is_content_type_allowed(content_type):
                        elapsed = time.monotonic() - t_start
                        logger.info(
                            "web_fetch blocked: content_type=%s, host=%s, elapsed=%.0fms",
                            content_type, _safe_url_for_logs(current_url), elapsed * 1000,
                        )
                        return _build_error_response(
                            "unsupported_content_type",
                            f"Content type '{content_type}' is not supported by web_fetch.",
                            "Use a document/PDF tool or a browser automation tool instead.",
                        )

                    # Extract text
                    raw = response.text
                    title, text = _strip_html(raw, extract_title=True)
                    text, was_truncated = _truncate_content(text, max_chars)

                    elapsed = time.monotonic() - t_start
                    logger.info(
                        "web_fetch success: host=%s, status=%d, content_type=%s, "
                        "char_count=%d, truncated=%s, elapsed=%.0fms",
                        _safe_url_for_logs(current_url), response.status_code,
                        content_type, len(text), was_truncated, elapsed * 1000,
                    )

                    return _build_success_response(
                        url=url,
                        final_url=final_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        text=text,
                        char_count=len(text),
                        truncated=was_truncated,
                        title=title or "",
                    )

                # Exceeded max redirects
                elapsed = time.monotonic() - t_start
                logger.info(
                    "web_fetch blocked: redirects=%d, host=%s, elapsed=%.0fms",
                    redirect_count, _safe_url_for_logs(url), elapsed * 1000,
                )
                return _build_error_response(
                    "too_many_redirects",
                    f"Exceeded maximum of {MAX_REDIRECTS} redirects.",
                    "The URL may be in a redirect loop. Try a different URL.",
                )

        except httpx.TimeoutException:
            elapsed = time.monotonic() - t_start
            logger.info(
                "web_fetch timeout: host=%s, elapsed=%.0fms",
                _safe_url_for_logs(url), elapsed * 1000,
            )
            return _build_error_response(
                "timeout",
                f"Request to {url} timed out after {WEB_FETCH_CONFIG['timeout_seconds']}s.",
                "Try again or try a different URL.",
            )
        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - t_start
            logger.info(
                "web_fetch http_error: host=%s, status=%d, elapsed=%.0fms",
                _safe_url_for_logs(url), e.response.status_code, elapsed * 1000,
            )
            return _build_error_response(
                "http_error",
                f"HTTP {e.response.status_code} when fetching {_safe_url_for_logs(url)}.",
                "Check the URL is correct and the page is publicly accessible.",
            )
        except Exception as e:
            elapsed = time.monotonic() - t_start
            logger.info(
                "web_fetch error: host=%s, error=%s, elapsed=%.0fms",
                _safe_url_for_logs(url), type(e).__name__, elapsed * 1000,
            )
            return _build_error_response(
                "fetch_error",
                f"Failed to fetch {_safe_url_for_logs(url)}: {e}",
                "Verify the URL is valid and the site is reachable.",
            )


# Register the tool
builtin_tool_registry.register(WebFetchTool())
```

- [ ] **Step 4: Update `__init__.py` to import web module**

```python
# Modify: backend/app/mcp/builtin/__init__.py
from .registry import builtin_tool_registry
from . import exec, docs, system, ppt, excel, web

__all__ = ["builtin_tool_registry"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_web_fetch_unit.py -v
```
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/builtin/web.py backend/app/mcp/builtin/__init__.py backend/tests/test_web_fetch_unit.py
git commit -m "feat: add builtin:web_fetch tool with JSON response envelope, redirect validation, content-type safeguards, and byte caps"
```

---

## Chunk 3: Registry Integration Verification

### Task 3: Verify end-to-end tool registry integration

**Files:**
- Modify: `backend/tests/test_tool_registry_integration.py` (append tests)

- [ ] **Step 1: Write integration test**

```python
# Append to backend/tests/test_tool_registry_integration.py

@pytest.mark.asyncio
async def test_registry_includes_web_fetch(registry, mock_mcp_manager):
    """Test that web_fetch is available as a builtin tool."""
    mock_agent = MagicMock()
    mock_agent.enabled_tools = ["builtin:web_fetch"]
    
    with patch("app.mcp.registry.agent_store") as mock_store:
        mock_store.get_agent.return_value = mock_agent
        tools = await registry.get_tools_for_agent("agent-1")
        
        assert len(tools) == 1
        assert tools[0].name == "web_fetch"
        assert isinstance(tools[0], BuiltinTool)

@pytest.mark.asyncio
async def test_web_fetch_in_all_metadata(registry, mock_mcp_manager):
    """Test that web_fetch appears in the all-tools metadata endpoint."""
    metadata = await registry.get_all_available_tools_metadata()
    web_fetch_meta = next((m for m in metadata if m["name"] == "web_fetch"), None)
    assert web_fetch_meta is not None
    assert web_fetch_meta["id"] == "builtin:web_fetch"
    assert web_fetch_meta["server"] == "builtin"
```

- [ ] **Step 2: Run integration test**

```bash
cd backend && python -m pytest tests/test_tool_registry_integration.py::test_registry_includes_web_fetch tests/test_tool_registry_integration.py::test_web_fetch_in_all_metadata -v
```
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_tool_registry_integration.py
git commit -m "test: add integration tests for web_fetch tool in registry"
```

---

## Chunk 4: Playwright MCP Template

### Task 4: Add Playwright MCP template to `DEFAULT_TEMPLATES`

**Files:**
- Modify: `backend/app/mcp/templates.py`
- Test: `backend/tests/test_api_mcp_unit.py`

**Design decisions:**
- Template ID: `playwright-mcp-browser`
- Supports both public web and enterprise intranet — Playwright runs a local browser that can reach any network the host machine can access
- Default args: `["-y", "@playwright/mcp"]`
- Transport: `stdio` (local npx process)
- This template is the foundation for enterprise intranet form automation: once configured, Agent can use `browser_navigate`, `browser_snapshot`, `browser_fill`, `browser_click` to intelligently operate intranet web pages based on natural language prompts

- [ ] **Step 1: Write the template test**

```python
# Append to backend/tests/test_api_mcp_unit.py

def test_playwright_mcp_template_exists():
    from app.mcp.templates import list_templates
    templates = list_templates()
    playwright_template = next((t for t in templates if t.id == "playwright-mcp-browser"), None)
    assert playwright_template is not None
    assert playwright_template.name == "Playwright MCP (Browser)"

def test_playwright_mcp_template_renders():
    from app.mcp.templates import render_template
    result = render_template(
        "playwright-mcp-browser",
        {
            "serverName": "playwright",
            "command": "npx",
            "argsJson": '["-y", "@playwright/mcp"]',
        }
    )
    rendered = result.rendered_config
    assert rendered["name"] == "playwright"
    assert rendered["transport"] == "stdio"
    assert rendered["command"] == "npx"
    assert "args" in rendered
    assert len(rendered["args"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_mcp_unit.py::test_playwright_mcp_template_exists tests/test_api_mcp_unit.py::test_playwright_mcp_template_renders -v
```
Expected: FAIL (template not found)

- [ ] **Step 3: Add the template to `templates.py`**

Insert before the closing `]` of `DEFAULT_TEMPLATES` (after the `custom-company-mcp` template):

```python
    McpTemplate(
        id="playwright-mcp-browser",
        name="Playwright MCP (Browser)",
        description=(
            "A browser automation MCP server built on Playwright. "
            "Enables agents to navigate pages, click elements, fill forms, "
            "take screenshots, and extract data through a local browser session."
        ),
        provider="microsoft",
        deployment="local",
        fields=[
            _field("serverName", "Server Name", required=True, default_value="playwright"),
            _field(
                "transport",
                "Transport",
                type="select",
                required=True,
                default_value="stdio",
                options=["stdio"],
                help_text="Playwright MCP runs locally via npx.",
            ),
            _field("command", "Command", required=True, default_value="npx", placeholder="npx"),
            _field(
                "argsJson",
                "Args (JSON Array)",
                type="json",
                required=True,
                default_value='["-y", "@playwright/mcp"]',
                help_text='Default runs the latest Playwright MCP server. Add flags like "--browser=chromium" if needed.',
            ),
            _field(
                "envJson",
                "Env (JSON Object)",
                type="json",
                default_value="{}",
                help_text="Optional: set PLAYWRIGHT_BROWSERS_PATH to a custom browser binary location.",
            ),
        ],
    ),
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_api_mcp_unit.py::test_playwright_mcp_template_exists tests/test_api_mcp_unit.py::test_playwright_mcp_template_renders -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/mcp/templates.py backend/tests/test_api_mcp_unit.py
git commit -m "feat: add Playwright MCP browser template to MCP marketplace templates"
```

---

## Chunk 5: Capability Routing — `CAP_WEB_FETCH` / `CAP_WEB_SEARCH` / `CAP_BROWSER_AUTOMATION`

### Task 5: Wire web tool capabilities into model routing

**Files:**
- Modify: `backend/app/services/llm/capabilities.py`
- Modify/Create: `backend/tests/test_capabilities_unit.py`

**Design decisions:**
- Introduce three distinct capability constants:
  - `CAP_WEB_FETCH = "web_fetch"` — for URL retrieval tools (e.g., `builtin:web_fetch`)
  - `CAP_WEB_SEARCH = "web_search"` — for search-engine-backed tools (e.g., future `builtin:web_search`)
  - `CAP_BROWSER_AUTOMATION = "browser_automation"` — for browser-interaction tools (e.g., Playwright MCP)
- `TOOL_CAPABILITY_MAP` maps tool IDs to their semantic capability constants
- `detect_capabilities_from_tools()` derives required model capabilities from an agent's enabled tools
- Models may need `CAP_WEB_SEARCH` natively, but do NOT need it for `CAP_WEB_FETCH` (the platform provides the tool)
- The existing `CAP_WEB_SEARCH` constant is preserved (was orphaned; now properly wired)

- [ ] **Step 1: Write capability detection tests**

```python
# backend/tests/test_capabilities_unit.py

from app.services.llm.capabilities import (
    detect_capabilities_from_tools,
    CAP_WEB_FETCH,
    CAP_WEB_SEARCH,
    CAP_BROWSER_AUTOMATION,
)

def test_capability_constants_defined():
    """All three web capability constants should be defined."""
    assert CAP_WEB_FETCH == "web_fetch"
    assert CAP_WEB_SEARCH == "web_search"
    assert CAP_BROWSER_AUTOMATION == "browser_automation"
    # Ensure they are distinct
    assert len({CAP_WEB_FETCH, CAP_WEB_SEARCH, CAP_BROWSER_AUTOMATION}) == 3

def test_detect_web_fetch_capability():
    """builtin:web_fetch should map to CAP_WEB_FETCH."""
    caps = detect_capabilities_from_tools(["builtin:web_fetch"])
    assert CAP_WEB_FETCH in caps

def test_detect_web_search_capability():
    """future builtin:web_search should map to CAP_WEB_SEARCH."""
    caps = detect_capabilities_from_tools(["builtin:web_search"])
    assert CAP_WEB_SEARCH in caps

def test_detect_no_web_capability_for_docs():
    """Document tools should not trigger web capabilities."""
    caps = detect_capabilities_from_tools([
        "builtin:docs_search",
        "builtin:docs_read",
        "builtin:docs_list",
    ])
    assert CAP_WEB_FETCH not in caps
    assert CAP_WEB_SEARCH not in caps
    assert CAP_BROWSER_AUTOMATION not in caps

def test_detect_no_web_capability_for_empty():
    """Empty tool list should produce no web capabilities."""
    caps = detect_capabilities_from_tools([])
    assert len(caps) == 0

def test_detect_multiple_tools_dedupes_capabilities():
    """Duplicate tools should not duplicate capabilities."""
    caps = detect_capabilities_from_tools([
        "builtin:web_fetch",
        "builtin:web_fetch",
    ])
    assert caps.count(CAP_WEB_FETCH) == 1

def test_detect_mixed_tools():
    """Multiple distinct web tools should produce distinct capabilities."""
    caps = detect_capabilities_from_tools([
        "builtin:web_fetch",
        "builtin:web_search",
        "mcp:playwright",
    ])
    assert CAP_WEB_FETCH in caps
    assert CAP_WEB_SEARCH in caps
    assert CAP_BROWSER_AUTOMATION in caps
    assert len(caps) == 3

def test_detect_playwright_mcp():
    """Playwright MCP should map to CAP_BROWSER_AUTOMATION."""
    caps = detect_capabilities_from_tools(["mcp:playwright"])
    assert CAP_BROWSER_AUTOMATION in caps

def test_detect_unknown_tool_no_effect():
    """Unknown tool IDs should not produce capabilities."""
    caps = detect_capabilities_from_tools(["builtin:unknown_tool"])
    assert len(caps) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_capabilities_unit.py -v
```
Expected: FAIL (functions/constants not defined)

- [ ] **Step 3: Update `capabilities.py`**

```python
# Update backend/app/services/llm/capabilities.py

CAP_WEB_FETCH = "web_fetch"
CAP_WEB_SEARCH = "web_search"
CAP_BROWSER_AUTOMATION = "browser_automation"

TOOL_CAPABILITY_MAP = {
    "builtin:web_fetch": CAP_WEB_FETCH,
    "builtin:web_search": CAP_WEB_SEARCH,
    "mcp:playwright": CAP_BROWSER_AUTOMATION,
}


def detect_capabilities_from_tools(enabled_tools: list[str]) -> list[str]:
    """
    Derive model capabilities needed based on the agent's enabled tools.
    
    Returns a sorted, deduplicated list of capability constants.
    Example: if enabled_tools contains builtin:web_fetch, returns [CAP_WEB_FETCH].
    """
    caps: set[str] = set()
    for tool_id in enabled_tools:
        cap = TOOL_CAPABILITY_MAP.get(tool_id)
        if cap:
            caps.add(cap)
    return sorted(caps)
```

**Note:** The existing `CAP_WEB_SEARCH` constant (if previously defined as `"web_search"`) must be updated to match the new value. Check for other references to the old constant and update them accordingly. If the constant is used in model routing (e.g., checking if a model `has_web_search`), those checks should now reference the appropriate capability (`CAP_WEB_SEARCH` for native search models, `CAP_WEB_FETCH` for tool-based fetch).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_capabilities_unit.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/capabilities.py backend/tests/test_capabilities_unit.py
git commit -m "feat: introduce CAP_WEB_FETCH/CAP_WEB_SEARCH/CAP_BROWSER_AUTOMATION capability model and tool detection helper"
```

---

## Chunk 6: End-to-End Regression & Manual QA

### Task 6: Full regression and manual verification

- [ ] **Step 1: Run full pytest regression**

```bash
cd backend && python -m pytest tests/ -v --timeout=60
```
Expected: ALL PASS (no regressions)

- [ ] **Step 2: Manual UI verification**
  1. Start the backend and frontend dev servers
  2. Open the Agents UI, create or edit an Agent
  3. Verify `web_fetch` appears in the tool picker with correct name and description
  4. Verify `max_chars` appears as an optional integer parameter
  5. Enable `web_fetch` on the Agent and save
  6. Start a chat with the Agent and ask: "Fetch the content of https://example.com"
  7. Verify:
     - The fetch executes (visible in tool execution trace)
     - The response is a structured JSON with `ok: true`, `title`, `text`, `char_count`, etc.
     - The Agent can reason over the returned content
  8. Test an error case: ask the Agent to "Fetch http://127.0.0.1/admin"
     - Verify the response shows `ok: false` with `error_code: "private_ip_blocked"`
  9. Verify the Playwright MCP template appears in MCP Templates UI with correct fields
  10. Verify the capability routing change does not break existing Agent model selection
  11. **Intranet form automation smoke test** (if intranet environment available):
     - Configure Playwright MCP server via the template
     - Enable Playwright tools on a test Agent
     - Ask: "Go to http://[intranet-url]/form, fill in the name field with 'Test', and tell me what the submit button says"
     - Verify `browser_navigate`, `browser_snapshot`, `browser_fill` execute in trace
     - Verify the Agent correctly reports the submit button text

---

## 3. Implementation Summary

| Chunk | New Files | Modified Files | Commits |
|:--|:--|:--|:--|
| 1. Web Guardrails | `builtin/_web_guards.py`, `tests/test_web_guards_unit.py` | — | 1 |
| 2. WebFetchTool | `builtin/web.py`, `tests/test_web_fetch_unit.py` | `builtin/__init__.py` | 1 |
| 3. Registry Integration | — | `tests/test_tool_registry_integration.py` | 1 |
| 4. Playwright MCP Template | — | `templates.py`, `tests/test_api_mcp_unit.py` | 1 |
| 5. Capability Routing | — | `capabilities.py`, `tests/test_capabilities_unit.py` | 1 |
| 6. Regression & QA | — | — | — (manual) |

**Total: 4 new files, 6 modified files, 5 commits**

---

## 4. Success Criteria

1. `builtin:web_fetch` appears in `GET /api/mcp/tools` with `id: "builtin:web_fetch"`, `server: "builtin"`
2. `web_fetch` can be enabled on any Agent via the Agents UI tool picker
3. SSRF attacks via literal private IPs are blocked (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, [::1])
4. SSRF attacks via hostname DNS resolution to private IPs are blocked (localhost, metadata.google.internal, etc.)
5. Redirects to private/internal IPs are blocked (each redirect target validated)
6. Unsupported content types (PDF, images, zip, video, etc.) are rejected with a clear error
7. Response size exceeding byte cap (1 MB) is rejected before downloading the body
8. Both success and error responses follow a consistent JSON envelope (`ok`, `error_code`/`status_code`, etc.)
9. Content is truncated at `max_chars` (clamped to [500, 50000]) with `truncated: true` in the response
10. Tool logs include safe debugging metadata (`host`, `status_code`, `content_type`, `elapsed_ms`, `truncated`, `error_code`) without leaking response bodies or sensitive query strings
11. Playwright MCP template appears in `GET /api/mcp/templates` with `id: "playwright-mcp-browser"`
12. `CAP_WEB_FETCH` is derivable from an agent's enabled tool list via `detect_capabilities_from_tools(["builtin:web_fetch"])`
13. `CAP_WEB_SEARCH` and `CAP_BROWSER_AUTOMATION` are defined and distinct from `CAP_WEB_FETCH`
14. Full regression suite passes with no regressions
15. Existing `CAP_WEB_SEARCH` constant is no longer orphaned
16. Manual UI verification confirms the tool can be enabled and used by an Agent, with readable execution traces
17. Playwright MCP template is deployable and Agent can use browser tools (`browser_navigate`, `browser_snapshot`, `browser_fill`, `browser_click`) to intelligently fill forms on intranet pages driven by natural language prompts
18. `builtin:web_fetch` explicitly rejects internal/private URLs (documented as by-design for security — intranet scenarios use Playwright MCP instead)
