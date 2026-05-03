import json
import logging
import re
import time
import uuid
import asyncio
from typing import Optional

from pydantic_ai import Agent
from app.mcp.models import ServerConfig
from app.mcp.smart_paste_models import ParsedServerConfig, SmartPasteLlmEnvelope, SmartPasteResponse
from app.mcp.smart_paste_sanitizer import sanitize_headers, sanitize_env
from app.services.config_service import config_service
from app.services.model_factory import get_model

logger = logging.getLogger(__name__)

SMART_PASTE_SYSTEM_PROMPT = """\
你是一个 MCP (Model Context Protocol) 配置解析器。

## 你的任务
分析用户粘贴的文本，从中提取一个或多个 MCP Server 配置信息，返回结构化 JSON。

## 总体规则
- 输出必须严格符合给定 schema
- 如果无法确定字段值，不要猜测；保留为空，并在 missing_fields 中指出
- 如果文本中包含多个 MCP 配置，全部输出到 results
- 如果同一服务存在多种接入方式（如 stdio 和 streamable_http），可以分别输出多个候选项
- 普通网页 URL 不应误判为 MCP endpoint，只有明确语义指向 MCP 服务地址时才识别为 streamable_http

## Transport 判断规则
- 如果文本包含命令行格式（如 "npx ..."、"uvx ..."、"python -m ..."）或 "command"/"args" 字段 → transport = "stdio"
- 如果文本包含 HTTP/HTTPS URL 且语义明确为 MCP 端点 → transport = "streamable_http"
- 如果存在多个候选 transport，不要强行合并，分别输出

## 字段提取规则

### stdio 模式
- command: 提取最外层可执行命令
- args: 提取命令参数列表，保持顺序
- env: 提取环境变量；若值疑似敏感信息，改为 ${ENV_NAME}

### streamable_http 模式
- url: 提取完整的 HTTP/HTTPS MCP endpoint
- headers: 提取请求头；敏感值必须改为 ${ENV_NAME}
- env: 如果文本明确提到运行前需要设置环境变量，则提取

### 通用字段
- name: 生成简短、稳定、英文 kebab-case 名称
- enabled: 一律设为 false
- timeout: 默认 60.0
- confidence: 给出 0.0-1.0 的解析置信度
- hints: 提供简洁说明，至少包含 transport 识别结果
- warnings: 描述风险、冲突或敏感信息替换情况
- missing_fields: 列出当前仍需用户补充的关键字段

## 安全规则（极其重要）
- 任何看起来像 token、password、api key、secret、JWT、Bearer token、私钥片段的值，绝对不能原样输出
- 将其替换为 ${ENV_NAME} 占位符
- 对高风险 header（Authorization、X-API-Key 等）和高风险 env（名称含 token/secret/password/key），如存在值，必须输出占位符
- 在 warnings 或 hints 中提醒用户设置对应环境变量

## 输出要求
- 返回一个 JSON 对象
- 顶层只包含 results
- results 中每一项都必须符合 schema
- 如果无法识别任何有效 MCP 配置，返回 { "results": [] }
"""

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


def parse_smart_paste(raw_text: str, llm_enabled: bool = False) -> SmartPasteResponse:
    try:
        cleaned = preprocess_raw_text(raw_text)
    except SmartPasteInputError:
        return SmartPasteResponse(ok=False, error="请输入配置信息")

    rule_response = try_rule_parse(cleaned)
    if rule_response is not None:
        return rule_response

    if not llm_enabled:
        raise SmartPasteServiceUnavailable(
            "Smart Paste AI fallback is disabled. Rule parsing found no matches."
        )

    return SmartPasteResponse(ok=False, error="无法从输入中解析出有效的 MCP 配置，请检查输入内容或尝试手动配置。")


async def parse_with_llm(
    raw_text: str,
    provider: str,
    model_name: str,
    max_retries: int = 1,
) -> list[ParsedServerConfig]:
    model = get_model(provider, model_name)

    for attempt in range(max_retries + 1):
        agent = Agent(
            model=model,
            system_prompt=SMART_PASTE_SYSTEM_PROMPT,
            result_type=SmartPasteLlmEnvelope,
        )
        try:
            result = await asyncio.wait_for(
                agent.run(raw_text),
                timeout=8.0,
            )
            envelope = result.output
            if envelope is None or not isinstance(envelope, SmartPasteLlmEnvelope):
                if attempt < max_retries:
                    continue
                return []

            sanitized = []
            for item in envelope.results:
                item_dict = item.model_dump()
                item_dict["headers"] = sanitize_headers(item_dict.get("headers"))
                item_dict["env"] = sanitize_env(item_dict.get("env"))

                validated = _validate_with_server_config(item_dict)
                if validated is None:
                    continue

                parsed = _build_parsed_config(
                    validated,
                    index=item.source_index or 0,
                    confidence=item.confidence,
                    hints=item.hints or ["已通过 AI 解析识别 MCP 配置"],
                    warnings=(item.warnings or []) + (
                        ["部分字段无法通过校验，已被调整"] if validated != item_dict else []
                    ),
                )
                sanitized.append(parsed)
            return sanitized

        except (asyncio.TimeoutError, TimeoutError):
            if attempt < max_retries:
                continue
            raise SmartPasteTimeoutError("AI 解析超时，请重试或使用手动配置")
        except Exception:
            logger.exception("LLM parse attempt %d failed", attempt + 1)
            if attempt < max_retries:
                continue
            return []

    return []


async def parse_smart_paste_async(raw_text: str, llm_enabled: bool = False) -> SmartPasteResponse:
    try:
        cleaned = preprocess_raw_text(raw_text)
    except SmartPasteInputError:
        return SmartPasteResponse(ok=False, error="请输入配置信息")

    rule_response = try_rule_parse(cleaned)
    if rule_response is not None:
        return rule_response

    if not llm_enabled:
        raise SmartPasteServiceUnavailable(
            "Smart Paste AI fallback is disabled. Rule parsing found no matches."
        )

    llm_config = config_service.get_llm_config()
    provider = llm_config.get("llm_provider") or llm_config.get("provider") or "openai"
    model_name = llm_config.get("model") or llm_config.get(f"{provider}_model") or "gpt-4o"

    try:
        llm_results = await parse_with_llm(cleaned, provider, model_name)
    except SmartPasteTimeoutError:
        return SmartPasteResponse(ok=False, error="AI 解析超时，请重试或使用手动配置")
    except SmartPasteServiceUnavailable:
        raise

    if not llm_results:
        return SmartPasteResponse(
            ok=False,
            error="无法从输入中解析出有效的 MCP 配置，请检查输入内容或尝试手动配置。"
        )

    return SmartPasteResponse(ok=True, results=llm_results, parse_mode="ai")
