import json
import logging
import re
import time
import uuid
from typing import Optional

from app.mcp.models import ServerConfig
from app.mcp.smart_paste_models import ParsedServerConfig, SmartPasteResponse
from app.mcp.smart_paste_sanitizer import sanitize_headers, sanitize_env

logger = logging.getLogger(__name__)

ILLEGAL_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

KNOWN_STDIO_COMMANDS = {"npx", "uvx", "node", "python", "python3", "pipx", "deno", "bun"}


class SmartPasteInputError(ValueError):
    pass


class SmartPasteServiceUnavailable(RuntimeError):
    pass


class SmartPasteRateLimitError(RuntimeError):
    pass


class SmartPasteTimeoutError(TimeoutError):
    pass


def preprocess_raw_text(raw_text: str) -> str:
    cleaned = ILLEGAL_CONTROL_CHARS_RE.sub("", raw_text)
    if not cleaned.strip():
        raise SmartPasteInputError("请输入配置信息")
    return cleaned


def _generate_name(candidate: dict, index: int) -> str:
    if candidate.get("name") and isinstance(candidate["name"], str) and candidate["name"].strip():
        return candidate["name"].strip()
    transport = candidate.get("transport", "stdio")
    if transport == "streamable_http":
        url = candidate.get("url", "")
        parsed = re.search(r"https?://([^/]+)", str(url))
        if parsed:
            return parsed.group(1).replace(".", "-")
        return f"http-server-{index}"
    command = candidate.get("command", "command")
    args = candidate.get("args", [])
    if args and isinstance(args, list) and len(args) > 0:
        last_arg = str(args[-1])
        cleaned = last_arg.replace("@", "").replace("/", "-")
        if cleaned:
            return cleaned
    return f"{command}-server-{index}"


def _validate_with_server_config(candidate: dict) -> Optional[dict]:
    try:
        validated = ServerConfig(**{
            "name": candidate.get("name", "smart-paste"),
            "transport": candidate.get("transport", "stdio"),
            "command": candidate.get("command"),
            "args": candidate.get("args"),
            "url": candidate.get("url"),
            "headers": candidate.get("headers"),
            "env": candidate.get("env"),
            "enabled": False,
            "timeout": candidate.get("timeout", 60.0),
            "min_version": candidate.get("min_version"),
        })
        return validated.model_dump(exclude_none=True)
    except Exception:
        return None


def _build_parsed_config(candidate: dict, index: int, confidence: float, hints: list = None, warnings: list = None) -> ParsedServerConfig:
    name = _generate_name(candidate, index)
    transport = candidate.get("transport", "stdio")

    headers = sanitize_headers(candidate.get("headers"))
    env = sanitize_env(candidate.get("env"))

    missing_fields = []
    if transport == "stdio":
        if not candidate.get("command"):
            missing_fields.append("command")
    elif transport == "streamable_http":
        if not candidate.get("url"):
            missing_fields.append("url")

    return ParsedServerConfig(
        name=name,
        transport=transport,
        command=candidate.get("command"),
        args=candidate.get("args"),
        url=candidate.get("url"),
        headers=headers,
        env=env,
        enabled=False,
        timeout=candidate.get("timeout", 60.0),
        min_version=candidate.get("min_version"),
        confidence=confidence,
        hints=hints or [],
        warnings=warnings or [],
        missing_fields=missing_fields,
        source_index=index,
    )


def parse_json_blob(raw_text: str) -> list[ParsedServerConfig]:
    results = []
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return results

    candidates = []

    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        if "mcpServers" in data and isinstance(data["mcpServers"], dict):
            for name, cfg in data["mcpServers"].items():
                if isinstance(cfg, dict):
                    cfg = dict(cfg)
                    if "name" not in cfg:
                        cfg["name"] = name
                    candidates.append(cfg)
        elif "transport" in data or "command" in data or "url" in data:
            candidates = [data]

    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        candidate = dict(candidate)
        if "transport" not in candidate:
            if "url" in candidate and not candidate.get("command"):
                candidate["transport"] = "streamable_http"
            else:
                candidate["transport"] = "stdio"

        validated = _validate_with_server_config(candidate)
        if validated is None:
            continue

        parsed = _build_parsed_config(
            validated,
            index=idx,
            confidence=0.95,
            hints=["已通过 JSON 解析识别 MCP 配置"],
        )
        results.append(parsed)

    return results


def parse_command_snippet(raw_text: str) -> list[ParsedServerConfig]:
    results = []
    text = raw_text.strip()

    import shlex
    try:
        tokens = shlex.split(text)
    except ValueError:
        return results

    if not tokens:
        return results

    command = tokens[0]
    if command not in KNOWN_STDIO_COMMANDS and not command.endswith(".exe"):
        return results

    args = tokens[1:] if len(tokens) > 1 else []

    candidate = {
        "name": _generate_name({"command": command, "args": args}, 0),
        "transport": "stdio",
        "command": command,
        "args": args,
    }

    validated = _validate_with_server_config(candidate)
    if validated is None:
        return results

    parsed = _build_parsed_config(
        validated,
        index=0,
        confidence=0.90,
        hints=["已从命令行片段识别 stdio transport"],
    )
    results.append(parsed)
    return results


def parse_http_endpoint(raw_text: str) -> list[ParsedServerConfig]:
    results = []
    url_match = re.search(r"(https?://[^\s<>\"']+)", raw_text)
    if not url_match:
        return results

    url = url_match.group(1).rstrip(".,;:)")

    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return results

    candidate = {
        "name": _generate_name({"transport": "streamable_http", "url": url}, 0),
        "transport": "streamable_http",
        "url": url,
    }

    validated = _validate_with_server_config(candidate)
    if validated is None:
        return results

    parsed = _build_parsed_config(
        validated,
        index=0,
        confidence=0.80,
        hints=["已从 URL 识别 streamable_http transport"],
    )
    results.append(parsed)
    return results


def try_rule_parse(raw_text: str) -> Optional[SmartPasteResponse]:
    results = (
        parse_json_blob(raw_text)
        or parse_command_snippet(raw_text)
        or parse_http_endpoint(raw_text)
    )
    if results:
        return SmartPasteResponse(ok=True, results=results, parse_mode="rule")
    return None


def parse_smart_paste(raw_text: str) -> SmartPasteResponse:
    try:
        cleaned = preprocess_raw_text(raw_text)
    except SmartPasteInputError:
        return SmartPasteResponse(ok=False, error="请输入配置信息")

    rule_response = try_rule_parse(cleaned)
    if rule_response is not None:
        return rule_response

    return SmartPasteResponse(ok=False, error="无法从输入中解析出有效的 MCP 配置，请检查输入内容或尝试手动配置。")
