# 多模态图片问答增强实施计划（前后端一体化）

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏现有聊天主链路的前提下，将“上传图片 + 文本提问”升级为稳定、可观测、可灰度发布的生产级能力，并补齐仅图片提问、模型视觉能力治理与错误恢复体验。

**Architecture:** 采用“前端输入编排 + 后端多模态请求治理 + 模型能力门禁 + 统一观测契约”的分层方案。前端负责输入体验和能力提示，后端负责图片验证/标准化/路由/降级，双方通过 `/api/chat/stream` 的 `meta` 契约保持一致。全链路以 feature flag 控制灰度，支持快速回滚。

**Tech Stack:** SolidJS、TypeScript、FastAPI、Pydantic AI、SQLite、Pytest、Vitest、Playwright

---

## 1. 背景与问题定义

当前仓库已经具备图片问答基础链路，但存在以下工程缺口：

1. 输入层限制“必须有文本才能发送”，导致“仅图提问”不可用。
2. 对模型是否支持 vision 缺少明确门禁策略，用户体验依赖模型偶然行为。
3. 图片预处理与错误提示偏弱，问题定位和恢复路径不清晰。
4. 缺少围绕多模态的专项回归门禁（单测 + 前端状态测试 + E2E）。
5. 观测指标不足，无法量化“图片问答成功率/失败原因”。

本计划目标是补齐上述差距，形成可持续迭代的多模态能力底座。

---

## 2. 范围与边界（Scope / Non-Goals）

### 2.1 范围（In Scope）

1. 前端图片输入体验增强（含仅图片发送）。
2. 后端图片请求治理（校验、标准化、错误分类、可观测）。
3. 模型视觉能力判定与策略化降级。
4. 流式元数据契约增强（vision 相关字段）。
5. 测试与灰度发布机制补齐。

### 2.2 非目标（Out of Scope）

1. 本期不做 OCR 结构化抽取产品化。
2. 本期不引入外部对象存储（保持本地 `/files`）。
3. 本期不重构整体聊天 UI 风格，仅在输入与提示区域做功能增强。

---

## 3. 目标状态（Target State）

### 3.1 用户侧目标

1. 支持三种输入模式：仅文本、文本+图片、仅图片。
2. 上传后可见缩略图、数量、大小、删除操作。
3. 当模型不支持视觉时，得到明确提示与推荐动作（切换模型/自动降级策略）。
4. 图片失败场景可理解（格式/大小/解码失败/模型不支持）。

### 3.2 系统侧目标

1. 请求前完成图片校验与标准化，减少模型端无效失败。
2. 所有多模态决策可追踪：支持 vision 与否、是否降级、失败类型。
3. 关键路径有测试门禁，保证迭代稳定。

---

## 4. 技术方案总览

### 4.1 前端分层

1. 输入层（`ChatInput`）：负责附件操作、发送条件、即时反馈。
2. 状态层（`useChatState`）：负责图片编码、请求体组装、错误分流。
3. 展示层（`MessageItem`）：负责历史图片显示与异常占位反馈。

### 4.2 后端分层

1. API 层（`chat.py`）：多模态请求编排与流式契约输出。
2. 服务层（新增 `multimodal_service.py`）：图片校验、标准化、能力判定、错误分类。
3. 存储层（`image_handler.py` + `chat_service.py`）：上传、回读、消息关联、清理策略。

### 4.3 能力门禁策略

1. `supports_vision` 由模型配置能力字段判定（配置优先）。
2. `vision_enabled = supports_vision AND request_has_images`。
3. `request_has_images=true AND supports_vision=false` 时执行策略：
   - 默认策略：返回可解释错误并建议可用模型。
   - 可选策略（flag）：文本降级执行（忽略图片）并在 `meta` 标记降级。

---

## 5. 文件结构与职责映射

## Chunk 1: 后端多模态治理内核

### Task 1: 建立多模态治理服务

**Files:**
- Create: `backend/app/services/multimodal_service.py`
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/config_service.py`
- Test: `backend/tests/test_multimodal_service_unit.py`

- [ ] **Step 1: 编写失败测试（校验与判定）**

```python
def test_validate_images_rejects_too_large():
    ...

def test_decide_vision_enabled_matrix():
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `PYTHONPATH=backend pytest backend/tests/test_multimodal_service_unit.py -v`
Expected: FAIL（服务尚未实现）

- [ ] **Step 3: 实现最小可用服务**

```python
class MultimodalService:
    def validate_images(...)
    def normalize_images(...)
    def decide_vision(...)
```

- [ ] **Step 4: 在 chat API 接入服务调用**

Run: `PYTHONPATH=backend pytest backend/tests/test_multimodal_service_unit.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/multimodal_service.py backend/app/api/chat.py backend/app/services/config_service.py backend/tests/test_multimodal_service_unit.py
git commit -m "feat(multimodal): add image validation and vision gating service"
```

### Task 2: 扩展流式 meta 契约

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/contracts/api/chat_stream_response.json`
- Test: `backend/tests/test_api_chat_unit.py`

- [ ] **Step 1: 增加契约字段测试**

```python
assert meta["supports_vision"] is True
assert meta["vision_enabled"] is True
assert meta["image_count"] == 1
```

- [ ] **Step 2: 运行单测确认失败**

Run: `PYTHONPATH=backend pytest backend/tests/test_api_chat_unit.py -k vision_meta -v`
Expected: FAIL

- [ ] **Step 3: 实现字段输出**

```python
meta["supports_vision"] = supports_vision
meta["vision_enabled"] = vision_enabled
meta["image_count"] = len(validated_images)
meta["vision_fallback_mode"] = fallback_mode
```

- [ ] **Step 4: 回归通过**

Run: `PYTHONPATH=backend pytest backend/tests/test_api_chat_unit.py -k vision_meta -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/chat.py backend/contracts/api/chat_stream_response.json backend/tests/test_api_chat_unit.py
git commit -m "feat(chat): expose vision decision fields in stream meta"
```

## Chunk 2: 前端输入与可用性增强

### Task 3: 支持仅图片发送与附件管理优化

**Files:**
- Modify: `frontend/src/components/ChatInput.tsx`
- Modify: `frontend/src/hooks/useChatState.ts`
- Modify: `frontend/src/pages/Chat.tsx`
- Test: `frontend/src/hooks/useChatState.multimodal.test.ts`

- [ ] **Step 1: 先写失败测试（仅图片发送）**

```ts
it('allows submit when only images are attached', async () => {
  ...
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npm run test -- useChatState.multimodal.test.ts`
Expected: FAIL

- [ ] **Step 3: 实现发送条件与请求组装修正**

```ts
const hasText = input().trim().length > 0
const hasImages = imageAttachments().length > 0
if (!hasText && !hasImages) return
```

- [ ] **Step 4: 增强附件交互**

```ts
// 缩略图、删除单张、清空全部、大小提示
```

- [ ] **Step 5: 测试通过并提交**

Run: `cd frontend && npm run test -- useChatState.multimodal.test.ts`
Expected: PASS

```bash
git add frontend/src/components/ChatInput.tsx frontend/src/hooks/useChatState.ts frontend/src/pages/Chat.tsx frontend/src/hooks/useChatState.multimodal.test.ts
git commit -m "feat(frontend): support image-only submit and attachment UX"
```

### Task 4: 视觉能力提示与失败反馈

**Files:**
- Modify: `frontend/src/components/LLMSelector.tsx`
- Modify: `frontend/src/hooks/useLLMProviders.ts`
- Modify: `frontend/src/types.ts`
- Test: `frontend/src/components/LLMSelector.vision.test.tsx`

- [ ] **Step 1: 为模型数据增加 capability 字段测试**
- [ ] **Step 2: 展示视觉能力标识（如 Vision badge）**
- [ ] **Step 3: 在模型不支持时提供前置提醒**
- [ ] **Step 4: 跑测试并提交**

Run: `cd frontend && npm run test -- LLMSelector.vision.test.tsx`
Expected: PASS

---

## 6. 数据与配置设计

### 6.1 配置项（建议新增到 `backend/data/global_config.json.example`）

1. `feature_flags.multimodal_enabled`（默认 true）
2. `feature_flags.multimodal_image_only_submit_enabled`（默认 true）
3. `feature_flags.multimodal_vision_fallback_enabled`（默认 false）
4. `multimodal.max_image_count`（默认 10）
5. `multimodal.max_image_size_mb`（默认 10）
6. `multimodal.allowed_mime_types`（默认 jpg/png/webp/gif）

### 6.2 模型能力声明

在 `llm.models.{provider/model}.capabilities` 增加 `vision`，由后端统一读取，不允许前端自行猜测。

---

## 7. 错误模型与用户提示规范

### 7.1 错误分类（后端）

1. `IMAGE_TOO_LARGE`
2. `IMAGE_FORMAT_UNSUPPORTED`
3. `IMAGE_DECODE_FAILED`
4. `MODEL_VISION_UNSUPPORTED`
5. `MODEL_VISION_TEMPORARY_UNAVAILABLE`

### 7.2 用户提示（前端）

1. 可行动建议优先：切换模型、压缩图片、减少数量。
2. 错误文案统一映射，不直接透出底层异常字符串。
3. 流式阶段失败需保留上下文，不清空用户输入与附件历史。

---

## 8. 测试与验收计划

## Chunk 3: 测试门禁补齐

### Task 5: 后端测试矩阵

**Files:**
- Modify: `backend/tests/test_api_chat_unit.py`
- Create: `backend/tests/test_multimodal_service_unit.py`
- Create: `backend/tests/test_multimodal_integration.py`

- [ ] **Step 1: 单测覆盖**
  - 图片大小/格式边界
  - supports_vision 判定矩阵
  - fallback 行为分支
- [ ] **Step 2: API 流式契约测试**
  - meta 新字段存在性
  - 图文输入路径稳定
- [ ] **Step 3: 集成测试**
  - 历史回放携带图片
  - 图片缺失文件回退路径

Run: `PYTHONPATH=backend pytest backend/tests/test_multimodal_service_unit.py backend/tests/test_multimodal_integration.py -v`
Expected: PASS

### Task 6: 前端测试矩阵

**Files:**
- Create: `frontend/e2e/multimodal-image-chat.spec.ts`
- Create: `frontend/src/hooks/useChatState.multimodal.test.ts`
- Create: `frontend/src/components/ChatInput.multimodal.test.tsx`

- [ ] **Step 1: 单元测试**
  - 仅图片发送
  - 图片数量限制
  - 删除单张/清空
- [ ] **Step 2: E2E**
  - 上传图片 + 文本发送成功
  - 仅图片发送成功
  - 不支持视觉模型提示

Run: `cd frontend && npm run test && npm run test:e2e -- multimodal-image-chat.spec.ts`
Expected: PASS

---

## 9. 可观测性与运维

### 9.1 指标

1. `multimodal_request_total`
2. `multimodal_request_success_total`
3. `multimodal_request_failure_total{reason}`
4. `multimodal_vision_unsupported_total`
5. `multimodal_fallback_total`

### 9.2 日志字段

1. `chat_id`
2. `provider/model`
3. `image_count`
4. `supports_vision`
5. `vision_enabled`
6. `error_code`

### 9.3 告警建议

1. 5 分钟窗口内 `multimodal_request_failure_total` 异常升高报警。
2. `MODEL_VISION_UNSUPPORTED` 比例异常提示配置失真或模型池变更风险。

---

## 10. 发布与回滚策略

### 10.1 发布阶段

1. 阶段 A：仅开启后端校验与观测，不改变前端发送策略。
2. 阶段 B：灰度开启“仅图片发送”与模型视觉提示（10%-30%-100%）。
3. 阶段 C：按指标稳定性决定是否开启 fallback 策略。

### 10.2 回滚策略

1. 关闭 `multimodal_image_only_submit_enabled` 恢复旧交互。
2. 关闭 `multimodal_vision_fallback_enabled` 恢复严格失败路径。
3. 必要时关闭 `multimodal_enabled`，保留文本主链路。

---

## 11. 工作量评估（人天）

1. 后端多模态治理与契约：2.0 ~ 3.0 人天
2. 前端输入与提示增强：1.5 ~ 2.5 人天
3. 测试补齐与回归：1.5 ~ 2.0 人天
4. 灰度与运维观察：0.5 ~ 1.0 人天

**总计：5.5 ~ 8.5 人天（1 人）**  
**建议排期：2 周（含灰度观察）**

---

## 12. 完成定义（Definition of Done）

1. 支持仅图片发送并通过前后端回归测试。
2. 流式 `meta` 返回 vision 判定字段并有契约测试。
3. 模型不支持视觉时用户获得明确可执行提示。
4. 多模态核心指标可观测，具备告警阈值。
5. feature flag 可独立开关并验证回滚。

---

## 13. 执行顺序建议

1. 先做后端治理内核（校验 + 判定 + meta 契约）。
2. 再做前端发送条件与能力提示。
3. 最后补齐测试门禁与灰度开关。

---

## 14. 测试闭环追踪矩阵（2026-03-18 基线）

### 14.1 已完成项（代码与测试资产已存在）

| 测试目标 | 测试文件 | 状态 |
| :--- | :--- | :--- |
| 图片大小/格式/payload 校验 + vision 判定 | `backend/tests/test_multimodal_service_unit.py` | ✅ |
| 流式 meta 的 vision 字段契约 | `backend/tests/test_api_chat_unit.py::test_chat_stream_emits_vision_meta` | ✅ |
| 历史图片回放与缺失文件回退 | `backend/tests/test_multimodal_integration.py` | ✅ |
| 前端仅图片发送规则 | `frontend/src/hooks/useChatState.multimodal.test.ts` | ✅ |
| 前端附件策略与上传入口行为 | `frontend/src/components/ChatInput.multimodal.test.tsx` | ✅ |
| 视觉能力标识渲染 | `frontend/src/components/LLMSelector.vision.test.tsx` | ✅ |
| 前端多模态 E2E 基础入口 | `frontend/e2e/multimodal-image-chat.spec.ts` | ✅ |

### 14.2 待补强项（闭环升级到生产验收）

1. `frontend/e2e/multimodal-image-chat.spec.ts` 需补齐三类断言：
   - 上传图片 + 文本发送成功
   - 仅图片发送成功
   - 不支持视觉模型时提示或降级行为可见
2. 手工验收证据需归档：Case A-F 截图/录屏、执行环境、模型组合、日期与执行人。
3. 灰度验证需补齐：10% 窗口观测 `MODEL_VISION_UNSUPPORTED` 与多模态失败率趋势。

### 14.3 闭环执行命令（标准顺序）

```bash
PYTHONPATH=backend pytest backend/tests/test_multimodal_service_unit.py -v
PYTHONPATH=backend pytest backend/tests/test_api_chat_unit.py -k vision_meta -v
PYTHONPATH=backend pytest backend/tests/test_multimodal_integration.py -v
cd frontend && npm run test -- src/hooks/useChatState.multimodal.test.ts src/components/ChatInput.multimodal.test.tsx src/components/LLMSelector.vision.test.tsx
cd frontend && npx playwright test e2e/multimodal-image-chat.spec.ts
./check.sh
```

### 14.4 结果判定

1. 所有自动化命令通过。
2. UI 手工 Case A-F 全部通过。
3. 回滚开关验证通过（`multimodal_enabled`、`multimodal_vision_fallback_enabled`）。
4. 发布记录中存在完整测试证据与执行日志。

---

Plan complete and saved to `docs/plans/multimodal_image_qa_enhancement_plan_20260317.md`. Ready to execute.
