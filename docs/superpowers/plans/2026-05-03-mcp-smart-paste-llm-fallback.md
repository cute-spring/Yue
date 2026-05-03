# MCP Smart Paste — LLM Fallback + 前端敏感信息确认 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Smart Paste 中接入 pydantic_ai LLM 兜底解析，处理自然语言和半结构化输入；同时在前端增加粘贴后敏感信息检测与确认替换步骤，确保真实密钥永不离开浏览器。

**Architecture:** 后端新增 `parse_with_llm()` 函数，使用 `pydantic_ai` 的 `result_type` 模式调用 LLM，注入设计文档中定义的中文 system prompt，解析失败时最多重试 1 次。前端新增 `SENSITIVE_CHECK` 中间阶段，用正则扫描用户粘贴的文本，将疑似密钥值提示替换为 `${ENV_NAME}` 占位符，用户确认后才发送给后端。

**Tech Stack:** FastAPI, Pydantic, `pydantic_ai`, `OpenAIChatModel`, existing `config_service` / `get_model`, SolidJS, Vitest, Playwright.

---

## 0. 前置决策确认

开发前需要确认以下策略选择（当前计划按默认推荐值编写，若有变更请调整对应步骤）：

| 决策项 | 默认选择 | 说明 |
|--------|---------|------|
| Q1: 开关粒度 | **B)** 规则解析始终可用，仅 LLM 兜底受开关控制 | 修改 `api/mcp.py` 的开关判断位置 |
| Q2: Model 选择 | **A)** 使用 `get_llm_config()` 的默认 provider + model | 简单直接，与项目其他地方一致 |
| Q3: LLM 超时 | **A)** 8 秒 | 对大多数轻量模型足够 |
| Q4: 降级策略 | **C)** 使用 `result_type` 让 pydantic_ai 自动处理 | pydantic_ai 有内置 fallback |
| Q5: 脱敏严格度 | **A)** 替换 + warning（保留结果） | 最大化可用结果数 |

---

## 1. File Map

### Backend

- Modify: `backend/app/mcp/smart_paste_models.py`
- Modify: `backend/app/mcp/smart_paste_service.py`
- Modify: `backend/app/api/mcp.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`
- Test: `backend/tests/test_api_mcp_unit.py`

### Frontend

- Modify: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts`
- Modify: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`
- Test: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
- Test: `frontend/e2e/mcp-smart-paste.spec.ts`

---

## Chunk 1: LLM Envelope Model + System Prompt + Feature Flag Refinement

### Task 1: Add LLM Envelope Model and System Prompt

**Files:**
- Modify: `backend/app/mcp/smart_paste_models.py`
- Modify: `backend/app/mcp/smart_paste_service.py`

- [ ] **Step 1: Write failing tests for the LLM envelope model**

在 `backend/tests/test_smart_paste_service_unit.py` 末尾追加：

```python
# --- LLM envelope tests ---


def test_smart_paste_llm_envelope_accepts_empty_results():
    from app.mcp.smart_paste_models import SmartPasteLlmEnvelope

    envelope = SmartPasteLlmEnvelope(results=[])
    assert envelope.results == []


def test_smart_paste_llm_envelope_validates_nested_model():
    from app.mcp.smart_paste_models import SmartPasteLlmEnvelope

    envelope = SmartPasteLlmEnvelope(
        results=[{
            "name": "test-srv",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "pkg"],
            "confidence": 0.9,
        }]
    )
    assert len(envelope.results) == 1
    assert envelope.results[0].name == "test-srv"
    assert envelope.results[0].transport == "stdio"


def test_system_prompt_contains_security_rules():
    from app.mcp.smart_paste_service import SMART_PASTE_SYSTEM_PROMPT

    assert "安全" in SMART_PASTE_SYSTEM_PROMPT or "secret" in SMART_PASTE_SYSTEM_PROMPT.lower()
    assert "ENV_NAME" in SMART_PASTE_SYSTEM_PROMPT or "占位符" in SMART_PASTE_SYSTEM_PROMPT
    assert len(SMART_PASTE_SYSTEM_PROMPT) > 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && python -m pytest tests/test_smart_paste_service_unit.py -q -k "llm_envelope" --no-header
```

Expected: FAIL — `SmartPasteLlmEnvelope` 和 `SMART_PASTE_SYSTEM_PROMPT` 不存在。

- [ ] **Step 3: Add `SmartPasteLlmEnvelope` model to `smart_paste_models.py`**

```python
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, confloat


class SmartPasteRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=8000)


class ParsedServerConfig(BaseModel):
    name: str
    transport: Literal["stdio", "streamable_http"]
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: bool = False
    timeout: float = 60.0
    min_version: Optional[str] = None
    confidence: confloat(ge=0.0, le=1.0)
    hints: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    source_index: Optional[int] = None


class SmartPasteLlmEnvelope(BaseModel):
    """LLM 结构化输出的顶层容器，只包含 results 数组。"""
    results: List[ParsedServerConfig] = Field(default_factory=list)


class SmartPasteResponse(BaseModel):
    ok: bool
    results: List[ParsedServerConfig] = Field(default_factory=list)
    parse_mode: Literal["rule", "ai", "hybrid"] = "ai"
    error: Optional[str] = None
```

- [ ] **Step 4: Add `SMART_PASTE_SYSTEM_PROMPT` to `smart_paste_service.py`**

在 `smart_paste_service.py` 顶部（import 之后、exception class 之前）插入：

```python
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
```

- [ ] **Step 5: Re-run tests**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && python -m pytest tests/test_smart_paste_service_unit.py -q -k "llm_envelope or system_prompt" --no-header
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/smart_paste_models.py backend/app/mcp/smart_paste_service.py backend/tests/test_smart_paste_service_unit.py
git commit -m "feat: add LLM envelope model and system prompt for smart paste"
```

### Task 2: Refine Feature Flag to Allow Rule Parsing Without LLM

**目的：** 开关 `mcp_smart_paste_enabled=false` 时，规则解析仍然可用；仅 LLM 兜底被禁用。

**Files:**
- Modify: `backend/app/api/mcp.py`
- Test: `backend/tests/test_api_mcp_unit.py`

- [ ] **Step 1: Write failing test — rule parsing works even when flag is off**

在 `backend/tests/test_api_mcp_unit.py` 中追加：

```python
def test_parse_endpoint_returns_rule_result_even_when_flag_disabled(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": False}
        response = client.post("/api/mcp/parse", json={"raw_text": "npx -y @company/mcp"})
        assert response.status_code == 200
        assert response.json()["parse_mode"] == "rule"


def test_parse_endpoint_returns_error_when_flag_disabled_and_rule_fails(client, mock_mcp_manager):
    with patch("app.api.mcp.config_service") as mock_cs:
        mock_cs.get_feature_flags.return_value = {"mcp_smart_paste_enabled": False}
        response = client.post(
            "/api/mcp/parse",
            json={"raw_text": "用自然语言描述的一个 MCP 配置，规则解析无法处理"}
        )
        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && YUE_DATA_DIR=/tmp/yue_test_data python -m pytest tests/test_api_mcp_unit.py -q -k "flag_disabled" --no-header
```

Expected: FAIL — 规则解析被 503 拦截。

- [ ] **Step 3: Move feature flag check from route entry to LLM call site**

修改 `backend/app/api/mcp.py` 的 `parse_mcp_config` 函数：

```python
@router.post("/parse", response_model=SmartPasteResponse)
async def parse_mcp_config(request: SmartPasteRequest):
    trace_id = str(uuid.uuid4())

    try:
        flags = config_service.get_feature_flags()
        llm_enabled = flags.get("mcp_smart_paste_enabled", False)
        response = parse_smart_paste(request.raw_text, llm_enabled=llm_enabled)
        logger.info(
            "smart_paste_parse",
            extra={
                "trace_id": trace_id,
                "raw_text_length": len(request.raw_text),
                "parse_mode": response.parse_mode,
                "result_count": len(response.results),
            },
        )
        return response
    except SmartPasteInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SmartPasteRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except SmartPasteServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except SmartPasteTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
```

- [ ] **Step 4: Update `parse_smart_paste` signature in `smart_paste_service.py`**

```python
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

    # LLM fallback — to be implemented in Chunk 2
    return SmartPasteResponse(
        ok=False,
        error="无法从输入中解析出有效的 MCP 配置，请检查输入内容或尝试手动配置。"
    )
```

- [ ] **Step 5: Re-run tests**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && YUE_DATA_DIR=/tmp/yue_test_data python -m pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q --no-header
```

Expected: PASS (all 50+ tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mcp.py backend/app/mcp/smart_paste_service.py backend/tests/test_api_mcp_unit.py
git commit -m "refactor: allow rule parsing when smart paste flag is off"
```

---

## Chunk 2: LLM Fallback Service Integration

### Task 3: Implement `parse_with_llm()` Function

**Files:**
- Modify: `backend/app/mcp/smart_paste_service.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`

- [ ] **Step 1: Write failing tests for `parse_with_llm`**

在 `backend/tests/test_smart_paste_service_unit.py` 末尾追加：

```python
# --- LLM fallback tests ---


@pytest.mark.asyncio
async def test_parse_with_llm_returns_structured_results():
    from app.mcp.smart_paste_models import SmartPasteLlmEnvelope, ParsedServerConfig
    from app.mcp.smart_paste_service import parse_with_llm

    mock_model = MagicMock()
    mock_agent_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.output = SmartPasteLlmEnvelope(
        results=[
            ParsedServerConfig(
                name="test-service",
                transport="stdio",
                command="npx",
                args=["-y", "test-pkg"],
                confidence=0.85,
                hints=["解析自自然语言描述"],
            )
        ]
    )
    mock_agent_instance.run = AsyncMock(return_value=mock_result)

    with patch("app.mcp.smart_paste_service.get_model", return_value=mock_model), \
         patch("app.mcp.smart_paste_service.Agent", return_value=mock_agent_instance), \
         patch("app.mcp.smart_paste_service.config_service") as mock_cs:
        mock_cs.get_llm_config.return_value = {
            "llm_provider": "openai",
            "openai_model": "gpt-4o",
        }
        results = await parse_with_llm(
            raw_text="用 npx -y test-pkg 启动一个 stdio MCP 服务",
            provider="openai",
            model_name="gpt-4o",
        )
        assert len(results) == 1
        assert results[0].name == "test-service"
        assert results[0].transport == "stdio"


@pytest.mark.asyncio
async def test_parse_with_llm_retries_on_schema_validation_error():
    from app.mcp.smart_paste_models import SmartPasteLlmEnvelope, ParsedServerConfig
    from app.mcp.smart_paste_service import parse_with_llm

    mock_model = MagicMock()
    mock_agent_instance = MagicMock()
    bad_result = MagicMock()
    bad_result.output = None  # first attempt fails schema validation
    good_result = MagicMock()
    good_result.output = SmartPasteLlmEnvelope(
        results=[
            ParsedServerConfig(
                name="retry-service",
                transport="stdio",
                command="node",
                args=["server.js"],
                confidence=0.8,
            )
        ]
    )
    mock_agent_instance.run = AsyncMock(side_effect=[bad_result, good_result])

    with patch("app.mcp.smart_paste_service.get_model", return_value=mock_model), \
         patch("app.mcp.smart_paste_service.Agent", return_value=mock_agent_instance), \
         patch("app.mcp.smart_paste_service.config_service") as mock_cs:
        mock_cs.get_llm_config.return_value = {
            "llm_provider": "openai",
            "openai_model": "gpt-4o",
        }
        results = await parse_with_llm(
            raw_text="node server.js 作为 MCP 服务",
            provider="openai",
            model_name="gpt-4o",
        )
        assert len(results) == 1
        assert mock_agent_instance.run.call_count == 2


@pytest.mark.asyncio
async def test_parse_with_llm_returns_empty_on_total_failure():
    from app.mcp.smart_paste_service import parse_with_llm

    mock_model = MagicMock()
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(side_effect=Exception("model error"))

    with patch("app.mcp.smart_paste_service.get_model", return_value=mock_model), \
         patch("app.mcp.smart_paste_service.Agent", return_value=mock_agent_instance), \
         patch("app.mcp.smart_paste_service.config_service") as mock_cs:
        mock_cs.get_llm_config.return_value = {
            "llm_provider": "openai",
            "openai_model": "gpt-4o",
        }
        results = await parse_with_llm(
            raw_text="test",
            provider="openai",
            model_name="gpt-4o",
        )
        assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && python -m pytest tests/test_smart_paste_service_unit.py -q -k "parse_with_llm" --no-header
```

Expected: FAIL — `parse_with_llm` 不存在。

- [ ] **Step 3: Implement `parse_with_llm()` in `smart_paste_service.py`**

在 `smart_paste_service.py` 的 import 区域追加：

```python
import asyncio
from pydantic_ai import Agent
from app.services.config_service import config_service
from app.services.model_factory import get_model
from app.mcp.smart_paste_models import SmartPasteLlmEnvelope
```

在文件的末尾（`parse_smart_paste` 函数之后）添加：

```python
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
```

- [ ] **Step 4: Integrate `parse_with_llm` into `parse_smart_paste`**

修改 `parse_smart_paste` 函数将 LLM 兜底改为异步调用。由于 `parse_smart_paste` 目前是同步函数，新增异步版本 `parse_smart_paste_async`：

```python
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
```

同步版本 `parse_smart_paste` 保留，内部通过 `asyncio.get_event_loop()` 或直接返回 rule 结果（不触发 LLM 的路径）：

```python
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

    # LLM fallback requires async — route layer should use parse_smart_paste_async
    return SmartPasteResponse(
        ok=False,
        error="无法从输入中解析出有效的 MCP 配置，请检查输入内容或尝试手动配置。"
    )
```

- [ ] **Step 5: Update route to use async version**

修改 `backend/app/api/mcp.py` 的 `parse_mcp_config`：

```python
@router.post("/parse", response_model=SmartPasteResponse)
async def parse_mcp_config(request: SmartPasteRequest):
    trace_id = str(uuid.uuid4())

    try:
        flags = config_service.get_feature_flags()
        llm_enabled = flags.get("mcp_smart_paste_enabled", False)
        response = await smart_paste_service_async(request.raw_text, llm_enabled=llm_enabled)
        # ...
```

需要在 `api/mcp.py` 中更新 import：

```python
from app.mcp.smart_paste_service import (
    parse_smart_paste,
    parse_smart_paste_async as smart_paste_service_async,
    ...
)
```

- [ ] **Step 6: Re-run tests**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && python -m pytest tests/test_smart_paste_service_unit.py -q --no-header
```

Expected: 所有 LLM fallback 测试 PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/smart_paste_service.py backend/app/api/mcp.py backend/tests/test_smart_paste_service_unit.py
git commit -m "feat: add LLM fallback for smart paste parsing"
```

---

## Chunk 3: LLM Error Handling + Route Polishing

### Task 4: Add LLM Error Mapping and Edge Cases

**Files:**
- Modify: `backend/app/mcp/smart_paste_service.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`
- Test: `backend/tests/test_api_mcp_unit.py`

- [ ] **Step 1: Write failing tests for error mapping**

在 `backend/tests/test_smart_paste_service_unit.py` 末尾追加：

```python
@pytest.mark.asyncio
async def test_parse_with_llm_times_out():
    from app.mcp.smart_paste_service import parse_with_llm, SmartPasteTimeoutError

    mock_model = MagicMock()
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("app.mcp.smart_paste_service.get_model", return_value=mock_model), \
         patch("app.mcp.smart_paste_service.Agent", return_value=mock_agent_instance), \
         patch("app.mcp.smart_paste_service.config_service") as mock_cs:
        mock_cs.get_llm_config.return_value = {"llm_provider": "openai", "openai_model": "gpt-4o"}
        with pytest.raises(SmartPasteTimeoutError):
            await parse_with_llm("test", "openai", "gpt-4o", max_retries=0)


@pytest.mark.asyncio
async def test_parse_smart_paste_async_returns_ok_false_on_llm_failure():
    from app.mcp.smart_paste_service import parse_smart_paste_async

    with patch("app.mcp.smart_paste_service.parse_with_llm") as mock_llm, \
         patch("app.mcp.smart_paste_service.config_service") as mock_cs:
        mock_cs.get_llm_config.return_value = {"llm_provider": "openai", "openai_model": "gpt-4o"}
        mock_llm.return_value = []

        response = await parse_smart_paste_async("一些无法解析的文本", llm_enabled=True)
        assert response.ok is False
        assert response.parse_mode == "ai"


@pytest.mark.asyncio
async def test_parse_smart_paste_async_post_processes_llm_output():
    from app.mcp.smart_paste_models import ParsedServerConfig
    from app.mcp.smart_paste_service import parse_smart_paste_async

    with patch("app.mcp.smart_paste_service.parse_with_llm") as mock_llm, \
         patch("app.mcp.smart_paste_service.config_service") as mock_cs:
        mock_cs.get_llm_config.return_value = {"llm_provider": "openai", "openai_model": "gpt-4o"}
        mock_llm.return_value = [
            ParsedServerConfig(
                name="test", transport="stdio", command="npx",
                args=["-y", "pkg"], confidence=0.9,
            )
        ]

        response = await parse_smart_paste_async("npx -y pkg", llm_enabled=True)
        assert response.ok is True
        assert response.parse_mode == "ai"
        assert response.results[0].enabled is False
        assert response.results[0].timeout == 60.0
```

- [ ] **Step 2: Run tests to verify gaps**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && python -m pytest tests/test_smart_paste_service_unit.py -q -k "parse_smart_paste_async or parse_with_llm_times_out" --no-header
```

Expected: 已有 `parse_smart_paste_async` 的部分测试可能 PASS，但超时和 async 集成测试可能 FAIL。

- [ ] **Step 3: Ensure Snitizer is Called In LLM Post-Processing**

确认 `parse_with_llm` 函数中已调用 `sanitize_headers` 和 `sanitize_env`（已在 Step 3 实现中完成）。

- [ ] **Step 4: Re-run all tests**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && python -m pytest tests/test_smart_paste_service_unit.py -q --no-header && YUE_DATA_DIR=/tmp/yue_test_data python -m pytest tests/test_api_mcp_unit.py -q --no-header
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/mcp/smart_paste_service.py backend/tests/test_smart_paste_service_unit.py backend/tests/test_api_mcp_unit.py
git commit -m "test: cover LLM fallback error handling and async flows"
```

---

## Chunk 4: Frontend Sensitive Info Detection + Confirm UI

### Task 5: Add `detectSensitiveValues` and `applyReplacements` Helpers

**Files:**
- Modify: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts`
- Test: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`

- [ ] **Step 1: Write failing tests for sensitive detection helpers**

在 `McpSmartPasteModal.logic.test.ts` 末尾追加：

```ts
describe('detectSensitiveValues', () => {
  it('detects sk- style API keys', () => {
    const result = detectSensitiveValues('JIRA_TOKEN=sk-abc123def456');
    expect(result.length).toBe(1);
    expect(result[0].value).toBe('sk-abc123def456');
    expect(result[0].key).toBe('TOKEN');
  });

  it('detects Bearer tokens', () => {
    const result = detectSensitiveValues('Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def');
    expect(result.length).toBe(1);
    expect(result[0].placeholder).toBe('${AUTHORIZATION_TOKEN}');
  });

  it('suggests placeholder from surrounding env var name', () => {
    const result = detectSensitiveValues('JIRA_TOKEN=my-real-secret-value');
    expect(result.length).toBe(1);
    expect(result[0].placeholder).toBe('${JIRA_TOKEN}');
  });

  it('returns empty array for clean text', () => {
    const result = detectSensitiveValues('npx -y @company/mcp-server');
    expect(result).toEqual([]);
  });

  it('detects multiple sensitive values', () => {
    const result = detectSensitiveValues(
      'JIRA_TOKEN=sk-abc\nGITHUB_TOKEN=ghp_xyz123\ncommand=npx'
    );
    expect(result.length).toBe(2);
  });
});

describe('applyReplacements', () => {
  it('replaces detected values with placeholders', () => {
    const detections = [
      { value: 'sk-abc123', placeholder: '${JIRA_TOKEN}', key: 'JIRA_TOKEN' },
    ];
    const result = applyReplacements('JIRA_TOKEN=sk-abc123', detections);
    expect(result).toBe('JIRA_TOKEN=${JIRA_TOKEN}');
  });

  it('preserves non-matching text', () => {
    const detections = [
      { value: 'sk-abc', placeholder: '${TOKEN}', key: 'TOKEN' },
    ];
    const result = applyReplacements('command=npx\nTOKEN=sk-abc\nport=8080', detections);
    expect(result).toContain('command=npx');
    expect(result).toContain('port=8080');
    expect(result).toContain('${TOKEN}');
  });
});
```

需要更新 import：

```ts
import { validateSmartPasteInput, applyTransportChange, findNameConflicts, resolveConfidenceTone, detectSensitiveValues, applyReplacements } from './McpSmartPasteModal.logic';
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx vitest run src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts 2>&1 | tail -10
```

Expected: FAIL — `detectSensitiveValues` 和 `applyReplacements` 不存在。

- [ ] **Step 3: Implement `detectSensitiveValues` and `applyReplacements`**

在 `McpSmartPasteModal.logic.ts` 中追加：

```ts
export type SensitiveDetection = {
  value: string;
  placeholder: string;
  key: string;
  index: number;
};

const SENSITIVE_PATTERNS: { pattern: RegExp; keyFromMatch: (m: RegExpExecArray) => string }[] = [
  {
    pattern: /([A-Z_][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|API[_\-]?KEY))\s*[=:]\s*(sk-[a-zA-Z0-9]{20,})/gi,
    keyFromMatch: (m) => m[1] || 'TOKEN',
  },
  {
    pattern: /([A-Z_][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|API[_\-]?KEY))\s*[=:]\s*([a-zA-Z0-9_\-]{20,})/gi,
    keyFromMatch: (m) => m[1] || 'TOKEN',
  },
  {
    pattern: /(?:Authorization|X-API-Key|api-key)\s*[=:]\s*(Bearer\s+)?(eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+)/gi,
    keyFromMatch: (m) => 'AUTHORIZATION',
  },
  {
    pattern: /(?:Authorization|X-API-Key|api-key)\s*[=:]\s*(Bearer\s+)?(sk-[a-zA-Z0-9]{20,})/gi,
    keyFromMatch: (m) => 'AUTHORIZATION',
  },
];

const PASSWORD_PATTERN = /([A-Z_][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|API[_\-]?KEY))\s*[=:]\s*([^\s]{8,})/gi;

export const detectSensitiveValues = (text: string): SensitiveDetection[] => {
  const seen = new Set<string>();
  const results: SensitiveDetection[] = [];

  for (const { pattern, keyFromMatch } of SENSITIVE_PATTERNS) {
    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      const value = match[2] || match[3] || '';
      if (seen.has(value)) continue;
      seen.add(value);
      const key = keyFromMatch(match);
      results.push({
        value,
        placeholder: `\${${key}_TOKEN}`,
        key,
        index: match.index,
      });
    }
  }

  PASSWORD_PATTERN.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = PASSWORD_PATTERN.exec(text)) !== null) {
    const value = match[2] || '';
    if (
      seen.has(value) ||
      value.startsWith('${') ||
      /^(true|false|yes|no|on|off|\d+)$/i.test(value) ||
      value.includes('://') ||
      value.includes('@') && value.includes('.')
    ) {
      continue;
    }
    seen.add(value);
    const key = match[1] || 'SECRET';
    results.push({
      value,
      placeholder: `\${${key.toUpperCase().replace(/-/g, '_')}}`,
      key: key.toUpperCase().replace(/-/g, '_'),
      index: match.index,
    });
  }

  return results.sort((a, b) => a.index - b.index);
};

export const applyReplacements = (
  text: string,
  detections: SensitiveDetection[],
): string => {
  let result = text;
  for (const det of detections) {
    result = result.replace(det.value, det.placeholder);
  }
  return result;
};
```

- [ ] **Step 4: Re-run tests**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx vitest run src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts 2>&1 | tail -10
```

Expected: ALL PASS (10 + 8 = 18 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts
git commit -m "feat: add frontend sensitive value detection helpers"
```

### Task 6: Add SENSITIVE_CHECK Phase to Modal

**Files:**
- Modify: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`

- [ ] **Step 1: Update phase type and state**

在 `McpSmartPasteModal.tsx` 中，修改 `Phase` 类型和 `handleParse` 逻辑：

```tsx
type Phase = 'idle' | 'sensitive_check' | 'parsing' | 'preview' | 'saving';

// 新增 sensitiveDetections 状态
const [sensitiveDetections, setSensitiveDetections] = createSignal<SensitiveDetection[]>([]);
const [replacedText, setReplacedText] = createSignal('');
```

- [ ] **Step 2: Rewrite `handleParse` to include sensitive check**

```tsx
const handleParse = async () => {
  const validation = validateSmartPasteInput(rawText());
  if (validation.kind === 'empty') return;
  if (validation.kind === 'too_long') {
    setParseError('输入文本过长，请精简后重试');
    return;
  }

  setParseError(null);

  const detections = detectSensitiveValues(rawText());
  if (detections.length > 0) {
    setSensitiveDetections(detections);
    setReplacedText(applyReplacements(rawText(), detections));
    setPhase('sensitive_check');
    return;
  }

  await doParse(rawText());
};

const handleSensitiveReplaceAll = () => {
  const cleanText = applyReplacements(rawText(), sensitiveDetections());
  setRawText(cleanText);
  setPhase('idle');
  doParse(cleanText);
};

const handleSensitiveSendAnyway = () => {
  setPhase('idle');
  doParse(rawText());
};

const handleSensitiveBackToEdit = () => {
  setPhase('idle');
};

const doParse = async (text: string) => {
  setPhase('parsing');
  abortController = new AbortController();

  try {
    const response = await props.onParse(text, abortController.signal);
    if (response.ok && response.results.length > 0) {
      setResults(response.results);
      setPhase('preview');
    } else {
      setParseError(response.error || '无法从输入中解析出有效的 MCP 配置');
      setPhase('idle');
    }
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      setPhase('idle');
      return;
    }
    setParseError(e?.message || '解析失败，请重试');
    setPhase('idle');
  }
};
```

- [ ] **Step 3: Add the SENSITIVE_CHECK phase UI**

在 modal body 中，`Show when={phase() === 'idle' || phase() === 'parsing'}` 条件**之前**插入：

```tsx
<Show when={phase() === 'sensitive_check'}>
  <div class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
    <div class="flex items-center gap-2 mb-2">
      <span class="text-amber-600 font-semibold">⚠️</span>
      <span class="text-sm font-semibold text-amber-800">
        检测到 {sensitiveDetections().length} 处疑似敏感信息
      </span>
    </div>
    <p class="text-xs text-amber-700 mb-3">
      建议在发送解析前替换为环境变量占位符，保护密钥安全。替换后可在系统环境变量中设置真实值。
    </p>

    <div class="space-y-2 max-h-[200px] overflow-y-auto mb-3">
      <For each={sensitiveDetections()}>
        {(det) => (
          <div class="flex items-center gap-2 text-xs bg-white rounded p-2 border border-amber-100">
            <span class="text-red-600 font-mono bg-red-50 px-1.5 py-0.5 rounded max-w-[180px] truncate" title={det.value}>
              {det.value}
            </span>
            <span class="text-gray-400">→</span>
            <span class="text-emerald-600 font-mono bg-emerald-50 px-1.5 py-0.5 rounded">
              {det.placeholder}
            </span>
            <span class="text-gray-400 ml-auto text-[10px]">{det.key}</span>
          </div>
        )}
      </For>
    </div>

    <div class="text-xs text-gray-500 mb-3">
      <div class="font-medium mb-1">替换后预览：</div>
      <pre class="bg-white border rounded p-2 max-h-[120px] overflow-y-auto text-[11px] whitespace-pre-wrap font-mono">{replacedText()}</pre>
    </div>
  </div>
</Show>
```

- [ ] **Step 4: Add the SENSITIVE_CHECK phase footer buttons**

修改 footer buttons 区域，为 `sensitive_check` 阶段添加按钮：

```tsx
<Show when={phase() === 'sensitive_check'}>
  <button onClick={handleSensitiveBackToEdit} class="px-3 py-1.5 rounded-md border text-sm">
    返回编辑
  </button>
  <div class="flex gap-2">
    <button onClick={handleSensitiveSendAnyway} class="px-3 py-1.5 rounded-md border text-sm text-gray-500">
      跳过，直接发送
    </button>
    <button onClick={handleSensitiveReplaceAll} class="px-4 py-1.5 rounded-md bg-amber-600 text-white text-sm">
      一键全部替换
    </button>
  </div>
</Show>
```

- [ ] **Step 5: Add `SensitiveDetection` import to modal**

```tsx
import { validateSmartPasteInput, applyTransportChange, findNameConflicts, resolveConfidenceTone, detectSensitiveValues, applyReplacements } from './McpSmartPasteModal.logic';
import type { SensitiveDetection } from './McpSmartPasteModal.logic';
```

- [ ] **Step 6: Run tests + check diagnostics**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx vitest run src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts 2>&1 | tail -10
```

Expected: ALL 18 tests PASS.

检查 IDE diagnostics 确保无 TypeScript 错误。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts
git commit -m "feat: add sensitive value detection and confirmation step to smart paste modal"
```

---

## Chunk 5: End-to-End Tests + Final Verification

### Task 7: Update E2E Test to Cover Natural Language + Sensitive Check

**Files:**
- Create/Modify: `frontend/e2e/mcp-smart-paste.spec.ts`

- [ ] **Step 1: Add a new E2E test for the sensitive check flow**

在现有 E2E 文件中追加新测试：

```ts
test('smart paste detects sensitive values and replaces before parsing', async ({ page }) => {
  const mcpConfigs: any[] = [];
  const featureFlagsState: Record<string, boolean> = {
    chat_trace_ui_enabled: false,
    chat_trace_raw_enabled: false,
    mcp_smart_paste_enabled: true,
  };

  // ... (复用之前 E2E 的路由 mock，省略，实际文件中需完整写出)

  await page.route('**/api/mcp/parse', async (route) => {
    const body = route.request().postDataJSON() as any;
    // 验证发送给后端的文本中不包含 sk- 密钥
    expect(body.raw_text).not.toContain('sk-abc123');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        parse_mode: 'rule',
        results: [{
          name: 'secure-service',
          transport: 'stdio',
          command: 'npx',
          args: ['-y', 'test-pkg'],
          url: null, headers: null, env: null,
          enabled: false, timeout: 60, min_version: null,
          confidence: 0.9,
          hints: ['已识别为 stdio 模式'],
          warnings: [],
          missing_fields: [],
          source_index: 0,
        }],
      }),
    });
  });

  await page.goto('/settings');
  await page.getByRole('button', { name: 'MCP' }).click();

  await page.getByTestId('mcp-add-menu-button').click();
  await page.getByTestId('mcp-smart-paste-button').click();

  await page.getByTestId('smart-paste-textarea').fill('JIRA_TOKEN=sk-abc123\nnpx -y test-pkg');
  await page.getByTestId('smart-paste-parse-btn').click();

  // 应该进入 sensitive_check 阶段
  await expect(page.getByText('检测到 1 处疑似敏感信息')).toBeVisible();
  await expect(page.getByText('sk-abc123')).toBeVisible();

  // 点击一键替换
  await page.getByText('一键全部替换').click();

  // 解析结果中不应该包含原始密钥
  await expect(page.getByTestId('smart-paste-name-input')).toHaveValue('secure-service');
});
```

- [ ] **Step 2: Add E2E test for the "skip sensitive" flow**

```ts
test('smart paste allows skipping sensitive detection', async ({ page }) => {
  // ... (mock setup)

  await page.getByTestId('smart-paste-textarea').fill('JIRA_TOKEN=sk-abc\nnpx -y test-pkg');
  await page.getByTestId('smart-paste-parse-btn').click();

  await expect(page.getByText('检测到 1 处疑似敏感信息')).toBeVisible();
  await page.getByText('跳过，直接发送').click();

  // 直接进入预览（或解析中）
  // 这个测试验证"跳过"按钮不阻塞流程
});
```

- [ ] **Step 3: Run E2E tests**

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx playwright test e2e/mcp-smart-paste.spec.ts
```

Expected: 3 tests PASS（原有 1 个 + 新增 2 个）。

- [ ] **Step 4: Run full regression suite**

Backend:

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && YUE_DATA_DIR=/tmp/yue_test_data python -m pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py tests/test_config_service_unit.py -q --no-header
```

Frontend:

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx vitest run src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts src/pages/settings/types.test.ts src/pages/settings/settingsUtils.test.ts
```

Expected: ALL PASS (81 backend + 31+ frontend).

- [ ] **Step 5: IDE diagnostics check**

检查以下文件无 TypeScript 错误：
- `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`
- `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts`
- `frontend/src/pages/settings/types.ts`
- `frontend/src/pages/Settings.tsx`

- [ ] **Step 6: Manual smoke on real app**

启动开发服务器，手动测试以下场景：

| # | 输入 | 预期行为 |
|---|------|---------|
| 1 | `npx -y @test/pkg` | 规则解析直接返回，不进入 sensitive_check |
| 2 | `JIRA_TOKEN=sk-abc\nnpx -y pkg` | 进入 sensitive_check → 替换 → 解析成功 |
| 3 | `用 stdio 方式连 Jira MCP，命令 npx -y @jira/mcp，环境变量 JIRA_TOKEN`（不含真实 token 值） | 规则失败 → LLM 兜底 → 解析成功（需要 `mcp_smart_paste_enabled=true`） |
| 4 | `JIRA_TOKEN=sk-abc\ndescription text` | 进入 sensitive_check → 一键替换 → 规则失败 → LLM 兜底（或 ok=false 如果 LLM 未启用） |
| 5 | JSON 格式多服务配置 | 规则解析直接返回多条结果 |
| 6 | 空输入 → 点击解析 | 前端阻止，不发请求 |

- [ ] **Step 7: Commit**

```bash
git add frontend/e2e/mcp-smart-paste.spec.ts
git commit -m "test: cover smart paste sensitive check and natural language E2E"
```

---

## 2. Implementation Notes

1. **异步边界：** `parse_smart_paste()` 保持同步（给规则解析路径使用），`parse_smart_paste_async()` 是新的异步入口（route 层使用）。同步版本在需要 LLM 时抛出 `SmartPasteServiceUnavailable`（route 层应改用异步版本）。

2. **LLM 调用不阻塞规则解析：** `try_rule_parse()` 在 `parse_with_llm()` 之前执行。这意味着标准 JSON、命令行片段、单一 URL 等输入不需要任何 LLM 调用。

3. **pydantic_ai `result_type` 的行为：** pydantic_ai 的 `result_type=SmartPasteLlmEnvelope` 会在支持 structured output 的 provider（OpenAI、DeepSeek 等）上使用 `response_format: json_schema`，对不支持的 provider 使用内置 JSON mode fallback。不需要额外处理。

4. **前端 sensitive 检测不做确定性：** 前端的正则检测是启发式的，目标是减少常见泄密风险，不是 100% 覆盖。后端 sanitizer 仍然是最后一道防线。

5. **`doParse` 提取为独立函数：** 避免 `handleParse`、`handleSensitiveReplaceAll`、`handleSensitiveSendAnyway` 三处重复解析逻辑。

6. **已存在的 placeholder 不被二次替换：** `detectSensitiveValues` 的 `PASSWORD_PATTERN` 已经有 `value.startsWith('${')` 检查。

---

## 3. Final Verification Commands

在执行计划的所有步骤后，运行以下命令确保一切正常：

```bash
# Backend unit tests
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && YUE_DATA_DIR=/tmp/yue_test_data python -m pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py tests/test_config_service_unit.py -q

# Frontend unit tests
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx vitest run src/pages/settings/

# E2E tests
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npx playwright test e2e/mcp-smart-paste.spec.ts
```

---

## 4. Handoff Checklist

- [ ] JSON / 命令行 / URL 规则解析在任何开关状态下都可用
- [ ] LLM 兜底仅在 `mcp_smart_paste_enabled=true` 时触发
- [ ] LLM 兜底使用 system prompt 正确引导模型输出结构化结果
- [ ] LLM 返回的结果经过 sanitizer 二次脱敏
- [ ] LLM 失败时最多重试 1 次，仍失败则返回 `ok=false`
- [ ] LLM 超时（8s）触发 `SmartPasteTimeoutError` → route 返回 504
- [ ] 前端检测到敏感信息时进入 `sensitive_check` 阶段，不直接发送
- [ ] 「一键全部替换」将敏感值替换为 `${ENV_NAME}` 占位符
- [ ] 「跳过，直接发送」允许用户不替换直接发送
- [ ] 「返回编辑」让用户手动修改
- [ ] 0 处敏感信息时跳过中间步骤，直接进入解析
- [ ] E2E 验证敏感信息不会出现在发送给后端的请求体中
- [ ] 所有后端和前端单元测试通过
- [ ] 所有 TypeScript 诊断零错误

---

Plan complete and saved to `docs/superpowers/plans/2026-05-03-mcp-smart-paste-llm-fallback.md`. Ready to execute?

