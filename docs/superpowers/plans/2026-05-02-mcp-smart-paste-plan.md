# MCP Smart Paste Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Settings 的 MCP 面板中新增 Smart Paste 流程，让用户可以粘贴 JSON、命令行、URL 或自然语言描述，获得可编辑、默认禁用、可安全保存的 MCP 候选配置。

**Architecture:** 以增量方式交付 Smart Paste。后端先建立强约束模型、功能开关、规则解析和脱敏后处理，再接入 `pydantic_ai` 作为 LLM 兜底，并继续复用 `ServerConfig` 作为最终兼容性校验。前端新增 `McpSmartPasteModal`，通过三段式状态机完成粘贴、解析预览、勾选保存，并沿用现有 `/api/mcp/` 与 `/api/mcp/reload` 链路完成落库与刷新。

**Tech Stack:** FastAPI, Pydantic, `pydantic_ai`, existing `config_service`, existing MCP API/tests, SolidJS, Vitest, Playwright.

---

## 1. Scope Locks

本计划先锁定以下实现决策，避免开发过程中反复回滚边界：

- 增加功能开关 `mcp_smart_paste_enabled`，默认 `false`；只有部署侧确认 provider / proxy 留存策略满足要求后才启用。
- Smart Paste 的解析端点只负责返回候选项，不做持久化，也不主动启用 MCP。
- 解析成功后的每个候选项默认 `enabled=false`，且允许用户删除、编辑、勾选后批量保存。
- 首期不新增通用 `POST /api/mcp/validate-configs`；用户编辑后的结构错误在保存阶段通过现有 `ServerConfig` 校验返回，并在弹窗内保留状态。
- 名称冲突首期在前端保存前先与 `mcpStatus()` 做显式比对并阻止提交；不改变现有 `/api/mcp/` 的 upsert 语义，避免影响 Manual / Marketplace 既有行为。
- 首期可观测性只记录摘要信息，如 `trace_id`、输入长度、解析模式、结果数、风险标记；禁止记录 `raw_text` 原文。

## 2. File Map

### Backend

- Create: `backend/app/mcp/smart_paste_models.py`
- Create: `backend/app/mcp/smart_paste_sanitizer.py`
- Create: `backend/app/mcp/smart_paste_service.py`
- Modify: `backend/app/api/mcp.py`
- Modify: `backend/app/services/config_service.py`
- Test: `backend/tests/test_api_mcp_unit.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`

### Frontend

- Modify: `frontend/src/pages/settings/types.ts`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/settings/components/McpSettingsTab.tsx`
- Create: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`
- Create: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts`
- Test: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
- Test: `frontend/e2e/mcp-smart-paste.spec.ts`

## Chunk 1: Contracts And Gating

### Task 1: Add Smart Paste Feature Flag And Shared Contracts

**Files:**
- Modify: `backend/app/services/config_service.py`
- Modify: `frontend/src/pages/settings/types.ts`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Write the failing backend flag test**

```python
def test_get_feature_flags_includes_mcp_smart_paste_default_false():
    flags = config_service.get_feature_flags()
    assert flags["mcp_smart_paste_enabled"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_config_service_unit.py -q`
Expected: FAIL because `mcp_smart_paste_enabled` is missing.

- [ ] **Step 3: Add the backend feature flag**

```python
return {
    ...
    "mcp_smart_paste_enabled": _coerce_bool(
        flags.get("mcp_smart_paste_enabled"),
        False,
    ),
}
```

- [ ] **Step 4: Extend the frontend feature flag type**

```ts
export type FeatureFlags = {
  chat_trace_ui_enabled: boolean;
  chat_trace_raw_enabled: boolean;
  mcp_smart_paste_enabled: boolean;
};
```

- [ ] **Step 5: Pass the flag into MCP settings state**

```ts
const smartPasteEnabled = () => featureFlags().mcp_smart_paste_enabled;
```

- [ ] **Step 6: Re-run targeted tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_config_service_unit.py -q`
Expected: PASS.

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/types.test.ts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/config_service.py frontend/src/pages/settings/types.ts frontend/src/pages/Settings.tsx
git commit -m "feat: add smart paste feature flag contract"
```

### Task 2: Add Smart Paste Request And Response Models

**Files:**
- Create: `backend/app/mcp/smart_paste_models.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`

- [ ] **Step 1: Write the failing model tests**

```python
def test_smart_paste_request_rejects_oversized_input():
    with pytest.raises(ValidationError):
        SmartPasteRequest(raw_text="x" * 8001)

def test_parsed_server_config_defaults_to_disabled():
    item = ParsedServerConfig(name="demo", transport="stdio", command="npx", confidence=1.0)
    assert item.enabled is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_smart_paste_service_unit.py -q`
Expected: FAIL because model module does not exist.

- [ ] **Step 3: Create the Smart Paste models**

```python
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
```

- [ ] **Step 4: Add the envelope response**

```python
class SmartPasteResponse(BaseModel):
    ok: bool
    results: List[ParsedServerConfig] = Field(default_factory=list)
    parse_mode: Literal["rule", "ai", "hybrid"] = "ai"
    error: Optional[str] = None
```

- [ ] **Step 5: Re-run targeted tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_smart_paste_service_unit.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/smart_paste_models.py backend/tests/test_smart_paste_service_unit.py
git commit -m "feat: add smart paste models"
```

## Chunk 2: Rule Parsing And Security

### Task 3: Build Sanitizer And Secret-Redaction Helpers

**Files:**
- Create: `backend/app/mcp/smart_paste_sanitizer.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`

- [ ] **Step 1: Write the failing sanitizer tests**

```python
def test_redacts_bearer_header_values():
    sanitized = sanitize_headers({"Authorization": "Bearer sk-secret"})
    assert sanitized["Authorization"] == "${AUTHORIZATION_TOKEN}"

def test_rejects_private_key_input():
    assert contains_blocked_secret_material("-----BEGIN PRIVATE KEY-----")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_smart_paste_service_unit.py -q`
Expected: FAIL because sanitizer helpers do not exist.

- [ ] **Step 3: Implement blocked-pattern detection and placeholder normalization**

```python
SECRET_KEYWORDS = ("token", "secret", "password", "api-key", "authorization")

def to_env_placeholder(name: str, fallback: str = "MCP_SECRET") -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    return f"${{{normalized or fallback}}}"
```

- [ ] **Step 4: Implement recursive field sanitization**

```python
def sanitize_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
    if not headers:
        return headers
    return {
        key: to_env_placeholder(key)
        if is_sensitive_key(key) and not is_placeholder(value)
        else value
        for key, value in headers.items()
    }
```

- [ ] **Step 5: Add result-level warnings for redaction**

```python
if redacted:
    warnings.append("Detected sensitive values and replaced them with environment placeholders.")
```

- [ ] **Step 6: Re-run targeted tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_smart_paste_service_unit.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/smart_paste_sanitizer.py backend/tests/test_smart_paste_service_unit.py
git commit -m "feat: add smart paste sanitizer"
```

### Task 4: Implement Rule-First Parsing Service

**Files:**
- Create: `backend/app/mcp/smart_paste_service.py`
- Modify: `backend/app/mcp/models.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`

- [ ] **Step 1: Write the failing rule-parser tests**

```python
def test_parse_claude_desktop_json_to_stdio_result():
    response = parse_smart_paste('{"mcpServers":{"fs":{"command":"npx","args":["-y","pkg"]}}}')
    assert response.ok is True
    assert response.parse_mode == "rule"
    assert response.results[0].transport == "stdio"

def test_parse_single_url_to_streamable_http_result():
    response = parse_smart_paste("MCP endpoint: https://mcp.example.com/stream")
    assert response.results[0].transport == "streamable_http"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_smart_paste_service_unit.py -q`
Expected: FAIL because service does not exist.

- [ ] **Step 3: Add a preprocess phase**

```python
def preprocess_raw_text(raw_text: str) -> str:
    cleaned = ILLEGAL_CONTROL_CHARS_RE.sub("", raw_text)
    if not cleaned.strip():
        raise SmartPasteInputError("请输入配置信息")
    return cleaned
```

- [ ] **Step 4: Implement deterministic parsers in priority order**

```python
def try_rule_parse(raw_text: str) -> list[ParsedServerConfig]:
    return (
        parse_json_blob(raw_text)
        or parse_command_snippet(raw_text)
        or parse_http_endpoint(raw_text)
    )
```

- [ ] **Step 5: Reuse `ServerConfig` as the final compatibility gate**

```python
validated = ServerConfig(**candidate.model_dump(exclude={"confidence", "hints", "warnings", "missing_fields", "source_index"}))
```

- [ ] **Step 6: Normalize stdio/http outputs into a single candidate shape**

```python
return ParsedServerConfig(
    name=resolved_name,
    transport="stdio",
    command=command,
    args=args,
    env=sanitized_env,
    enabled=False,
    confidence=0.95,
    hints=["Recognized stdio transport from command snippet."],
)
```

- [ ] **Step 7: Allow `ServerConfig` to keep current API semantics unchanged**

Do not alter `ServerConfig` validation rules; only add tiny helper utilities if needed, such as a dump helper shared by route and Smart Paste service.

- [ ] **Step 8: Re-run targeted tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_smart_paste_service_unit.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/mcp/smart_paste_service.py backend/app/mcp/models.py backend/tests/test_smart_paste_service_unit.py
git commit -m "feat: add rule-first smart paste parser"
```

## Chunk 3: LLM Fallback And Parse API

### Task 5: Add LLM Fallback, Error Mapping, And Parse Route

**Files:**
- Modify: `backend/app/api/mcp.py`
- Modify: `backend/app/mcp/smart_paste_service.py`
- Test: `backend/tests/test_api_mcp_unit.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`

- [ ] **Step 1: Write the failing API tests**

```python
def test_parse_endpoint_returns_rule_result(client):
    response = client.post("/api/mcp/parse", json={"raw_text": "npx -y @company/mcp"})
    assert response.status_code == 200
    assert response.json()["parse_mode"] == "rule"

def test_parse_endpoint_returns_503_when_feature_disabled(client):
    response = client.post("/api/mcp/parse", json={"raw_text": "npx -y @company/mcp"})
    assert response.status_code == 503
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q`
Expected: FAIL because `/api/mcp/parse` is missing.

- [ ] **Step 3: Add a thin LLM client wrapper in the service**

```python
async def parse_with_llm(raw_text: str) -> list[ParsedServerConfig]:
    model = build_model_from_config(config_service.get_llm_config())
    agent = Agent(model=model, system_prompt=SMART_PASTE_SYSTEM_PROMPT, result_type=SmartPasteLlmEnvelope)
    result = await agent.run(raw_text)
    return result.output.results
```

- [ ] **Step 4: Keep fallback behavior strict**

```python
if rule_results:
    return SmartPasteResponse(ok=True, results=rule_results, parse_mode="rule")
if not feature_flags.get("mcp_smart_paste_enabled", False):
    raise SmartPasteServiceUnavailable("Smart Paste is disabled until AI retention requirements are approved.")
```

- [ ] **Step 5: Add route wiring and status mapping**

```python
@router.post("/parse", response_model=SmartPasteResponse)
async def parse_mcp_config(request: SmartPasteRequest):
    return await smart_paste_service.parse(request.raw_text)
```

- [ ] **Step 6: Map service exceptions to user-safe HTTP responses**

```python
except SmartPasteInputError as exc:
    raise HTTPException(status_code=400, detail=str(exc))
except SmartPasteRateLimitError as exc:
    raise HTTPException(status_code=429, detail=str(exc))
except SmartPasteServiceUnavailable as exc:
    raise HTTPException(status_code=503, detail=str(exc))
except SmartPasteTimeoutError as exc:
    raise HTTPException(status_code=504, detail=str(exc))
```

- [ ] **Step 7: Add summary-only logging**

```python
logger.info(
    "smart_paste_parse",
    extra={"trace_id": trace_id, "raw_text_length": len(raw_text), "parse_mode": mode, "result_count": len(results)},
)
```

- [ ] **Step 8: Re-run targeted backend tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/mcp.py backend/app/mcp/smart_paste_service.py backend/tests/test_api_mcp_unit.py backend/tests/test_smart_paste_service_unit.py
git commit -m "feat: expose smart paste parse api"
```

### Task 6: Add Backend Regression Coverage For Edge Cases

**Files:**
- Test: `backend/tests/test_smart_paste_service_unit.py`
- Test: `backend/tests/test_api_mcp_unit.py`

- [ ] **Step 1: Add edge-case tests**

```python
def test_parse_rejects_illegal_control_chars(): ...
def test_parse_redacts_authorization_header(): ...
def test_parse_keeps_partial_valid_results_and_drops_invalid_ones(): ...
def test_parse_returns_ok_false_when_nothing_is_extractable(): ...
```

- [ ] **Step 2: Run tests to verify gaps**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q`
Expected: FAIL on at least one uncovered edge case before implementation is completed.

- [ ] **Step 3: Implement the minimal fixes**

Prefer small changes in `smart_paste_service.py` and `smart_paste_sanitizer.py`; do not widen route responsibilities.

- [ ] **Step 4: Re-run the same test selection**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_api_mcp_unit.py backend/tests/test_smart_paste_service_unit.py backend/app/mcp/smart_paste_service.py backend/app/mcp/smart_paste_sanitizer.py
git commit -m "test: cover smart paste edge cases"
```

## Chunk 4: Frontend Modal And Save Flow

### Task 7: Add Frontend Smart Paste Types And Pure Logic Helpers

**Files:**
- Modify: `frontend/src/pages/settings/types.ts`
- Create: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts`
- Test: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`

- [ ] **Step 1: Write the failing logic tests**

```ts
it('blocks empty input locally', () => {
  expect(validateSmartPasteInput('   ').kind).toBe('empty');
});

it('clears mutually exclusive fields when transport changes', () => {
  expect(applyTransportChange(candidate, 'streamable_http').command).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
Expected: FAIL because helper file does not exist.

- [ ] **Step 3: Add Smart Paste frontend types**

```ts
export type ParsedMcpConfig = {
  name: string;
  transport: 'stdio' | 'streamable_http';
  command: string | null;
  args: string[] | null;
  url: string | null;
  headers: Record<string, string> | null;
  env: Record<string, string> | null;
  enabled: boolean;
  timeout: number;
  min_version: string | null;
  confidence: number;
  hints: string[];
  warnings: string[];
  missing_fields: string[];
  source_index?: number | null;
};
```

- [ ] **Step 4: Extract pure modal helpers**

```ts
export const validateSmartPasteInput = (rawText: string) => {
  const text = rawText.trim();
  if (!text) return { kind: 'empty' } as const;
  if (text.length > 8000) return { kind: 'too_long' } as const;
  return { kind: 'ok', text } as const;
};
```

- [ ] **Step 5: Re-run targeted tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/settings/types.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts
git commit -m "feat: add smart paste frontend contracts"
```

### Task 8: Build `McpSmartPasteModal` UI State Machine

**Files:**
- Create: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`
- Test: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`

- [ ] **Step 1: Add failing state-transition tests for the pure helpers**

```ts
it('marks low-confidence results as high risk below 0.6', () => {
  expect(resolveConfidenceTone(0.4)).toBe('danger');
});
```

- [ ] **Step 2: Run tests to verify the gap**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
Expected: FAIL because confidence helper is missing.

- [ ] **Step 3: Implement the modal skeleton**

```tsx
type McpSmartPasteModalProps = {
  existingNames: string[];
  onClose: () => void;
  onParse: (rawText: string, signal: AbortSignal) => Promise<SmartPasteResponse>;
  onSave: (configs: ParsedMcpConfig[]) => Promise<void>;
};
```

- [ ] **Step 4: Add the three-phase modal state machine**

```tsx
const [phase, setPhase] = createSignal<'idle' | 'parsing' | 'preview' | 'saving'>('idle');
const [rawText, setRawText] = createSignal('');
const [results, setResults] = createSignal<ParsedMcpConfig[]>([]);
```

- [ ] **Step 5: Wire parse cancellation and retry**

```tsx
const controller = new AbortController();
onCleanup(() => controller.abort());
```

- [ ] **Step 6: Add preview editing affordances**

Include:
- editable `name`, `transport`, `command`, `args`, `url`, `headers`, `env`
- result checkbox
- delete candidate
- confidence / warning / missing-field banners

- [ ] **Step 7: Re-run targeted tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts
git commit -m "feat: add smart paste modal"
```

### Task 9: Integrate Smart Paste Into Settings And Save Flow

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/settings/components/McpSettingsTab.tsx`
- Modify: `frontend/src/pages/settings/types.ts`

- [ ] **Step 1: Write a failing integration test for helper behavior**

Add pure helper coverage in `McpSmartPasteModal.logic.test.ts` for:

```ts
it('blocks save when selected names conflict with existing MCP names', () => {
  expect(findNameConflicts(['jira'], [{ name: 'jira' }])).toEqual(['jira']);
});
```

- [ ] **Step 2: Run frontend targeted tests to confirm the gap**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts src/pages/settings/types.test.ts`
Expected: FAIL because conflict helper or prop wiring is missing.

- [ ] **Step 3: Add the menu entry and prop plumbing**

```tsx
<Show when={props.smartPasteEnabled()}>
  <button onClick={() => props.setShowSmartPaste(true)}>Smart Paste (AI)</button>
</Show>
```

- [ ] **Step 4: Add parse and save handlers in `Settings.tsx`**

```ts
const parseMcpSmartPaste = async (rawText: string, signal: AbortSignal): Promise<SmartPasteResponse> => {
  const res = await fetch('/api/mcp/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_text: rawText }),
    signal,
  });
  return await res.json();
};
```

- [ ] **Step 5: Save selected candidates through the existing write path**

```ts
await fetch('/api/mcp/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(selectedConfigs),
});
await fetch('/api/mcp/reload', { method: 'POST' });
await fetchData();
```

- [ ] **Step 6: Block duplicate names before submit**

```ts
const conflicts = findNameConflicts(existingNames, selectedConfigs);
if (conflicts.length > 0) {
  setError(`Name already exists: ${conflicts.join(', ')}`);
  return;
}
```

- [ ] **Step 7: Re-run targeted frontend tests**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts src/pages/settings/types.test.ts src/pages/settings/settingsUtils.test.ts`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/settings/components/McpSettingsTab.tsx frontend/src/pages/settings/types.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts
git commit -m "feat: integrate smart paste into settings"
```

## Chunk 5: Verification And Release Readiness

### Task 10: Add End-To-End Coverage And Final Verification

**Files:**
- Create: `frontend/e2e/mcp-smart-paste.spec.ts`
- Test: `backend/tests/test_api_mcp_unit.py`
- Test: `backend/tests/test_smart_paste_service_unit.py`
- Test: `frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`

- [ ] **Step 1: Add the failing E2E happy-path spec**

```ts
test('smart paste parses stdio config and saves disabled entry', async ({ page }) => {
  await page.goto('/settings');
  await page.getByText('Smart Paste (AI)').click();
  await page.getByRole('textbox').fill('npx -y @anthropic/mcp-server-filesystem');
  await page.getByText('AI Parse').click();
  await page.getByText('Confirm And Save').click();
  await expect(page.getByText('filesystem')).toBeVisible();
});
```

- [ ] **Step 2: Run backend and frontend test suites separately**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q`
Expected: PASS.

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts`
Expected: PASS.

- [ ] **Step 3: Run the new E2E test**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test:e2e -- e2e/mcp-smart-paste.spec.ts`
Expected: PASS.

- [ ] **Step 4: Run a manual smoke checklist**

Check:
- empty input is blocked locally
- oversized input is blocked locally
- parse cancellation leaves no hanging spinner
- low-confidence warning renders
- duplicate names are blocked before save
- saved configs appear disabled by default
- no toast or network error echoes raw pasted secrets

- [ ] **Step 5: Run diagnostics on touched frontend files**

Use IDE diagnostics on:
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/settings/components/McpSettingsTab.tsx`
- `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`
- `frontend/src/pages/settings/types.ts`

Expected: no new TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_api_mcp_unit.py backend/tests/test_smart_paste_service_unit.py frontend/e2e/mcp-smart-paste.spec.ts frontend/src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts
git commit -m "test: cover smart paste end to end"
```

## 3. Implementation Notes

- Keep route responsibilities thin. All parsing, fallback, sanitization, and validation orchestration should live in `smart_paste_service.py`.
- Keep UI-only state logic out of JSX where practical. If a decision can be unit-tested without DOM, put it in `McpSmartPasteModal.logic.ts`.
- Prefer deterministic parsers before LLM fallback. The happy path for JSON, command snippets, and single URLs should not depend on model availability.
- Avoid touching `backend/app/mcp/manager.py`, template rendering, or existing Manual / Marketplace flows unless Smart Paste integration exposes a shared utility that clearly belongs there.
- Do not add raw pasted content to logs, exceptions, toasts, or analytics payloads.

## 4. Final Verification Commands

Run these before marking the feature ready for review:

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && pytest tests/test_api_mcp_unit.py tests/test_smart_paste_service_unit.py -q
```

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test -- src/pages/settings/components/modals/McpSmartPasteModal.logic.test.ts src/pages/settings/types.test.ts src/pages/settings/settingsUtils.test.ts
```

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm run test:e2e -- e2e/mcp-smart-paste.spec.ts
```

## 5. Handoff Checklist

- Smart Paste is hidden when `mcp_smart_paste_enabled=false`.
- Rule parsing works without LLM for JSON, command snippet, and single-URL inputs.
- LLM fallback only runs after rule parsing misses.
- Sensitive values are converted to placeholders before any response leaves the backend.
- Saved results are disabled by default and only include user-selected candidates.
- Duplicate names are blocked before save.
- Backend and frontend targeted tests pass.
- E2E happy path passes.

Plan complete and saved to `docs/superpowers/plans/2026-05-02-mcp-smart-paste-plan.md`. Ready to execute?
