# RCA-001: DeepSeek Reasoner 流式输出不完整修复报告

## 1. 问题描述
用户反馈在使用 `deepseek-reasoner` 模型生成复杂的 Coffee Shop Landing Page (HTML/Tailwind) 时，返回的 API 响应不完整，导致 HTML 代码在中间被截断，无法正常渲染。

- **模型**: `deepseek-reasoner`
- **任务类型**: 长文本生成 (Landing Page)
- **表现**: HTTP 响应提前结束，缺少结束标签。

---

## 2. 根因分析 (Root Cause)

经过复现和排查，该问题由以下两个层面的原因共同导致：

### 2.1 显式 Token 限制 (Hard Limit)
`deepseek-reasoner` 模型在生成最终答案前会产生大量的**内部推理内容 (Reasoning Content)**。
- 原始 `max_output_tokens` 设置为 **8192**。
- 对于生成 HTML Landing Page 这种本身就需要 15,000+ 字符的任务，加上推理内容的消耗，8192 的空间远不足以承载完整输出，导致模型在输出 HTML 时触发 Token 限制而被迫中断。

### 2.2 逻辑配置失效 (Logic Bug)
在 `backend/app/api/chat.py` 的流式处理逻辑中：
- 当模型因某些原因（如不支持工具使用）进入 **Fallback 逻辑** 时，`agent_no_tools.run_stream()` 调用未传递 `model_settings`。
- 这导致即使在配置文件中调高了 Token 限制，该限制在实际的流式传输中也未能生效，系统回退到了默认的较小限制。

---

## 3. 解决方案 (Solution)

### 3.1 配置层优化
在 [global_config.json](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/global_config.json) 中进行如下调整：
- 将 `deepseek-reasoner` 的 `max_output_tokens` 设定为 **8192**（这是 DeepSeek API 当前支持的最大硬限制）。
- 修正之前尝试设置 32768 导致 API 返回 400 错误（`Invalid max_tokens value`）的问题。

---

## 4. 核心解决方案：自动续写架构 (Auto-Continue Strategy)

由于 DeepSeek 的硬限制（8K）无法承载复杂生成任务，我们通过以下架构彻底解决截断问题：

### 6.1 方案核心思想
采用 **链式生成 (Chained Generation)** 模式。当后端检测到模型因长度限制（`finish_reason == "length"`）而中断时，前端展示“继续生成”按钮。

---

## 5. 最终实现方案 (Final Implementation)

### 5.1 前端：智能“继续生成”按钮
-   **组件**：`MessageItem.tsx`
-   **触发条件**：当消息的 `finish_reason === 'length'` 且为 `assistant` 角色且已停止打字时。
-   **交互逻辑**：点击按钮后，自动在输入框填入“继续”并触发提交。

### 5.2 后端：续传协议注入 (Continuation Protocol)
-   **服务**：`prompt_service.py` 中的 `PromptBuilder`。
-   **逻辑**：检测到用户输入为“继续”时，动态注入指令，要求模型从断点处无缝续写。

---

## 6. 验证结果
- **成功场景**: 用户在生成 15,000 字符的 HTML 时，第一次生成在 8,000 字符处被截断。点击“继续生成”后，模型从 `<!-- Tailwind CSS ...` 断点处完美接力，最终合成了完整的 Landing Page。

---

## 8. 新故障诊断：前端流式渲染冻结 (UI Freeze during Streaming)

在修复了后端的 Token 限制后，用户反馈了一个新的次生问题：API 流仍在持续输出数据，但前端 UI 界面停止了更新，看起来像是“卡住了”。

### 8.1 根因分析 (Root Cause)

1.  **SSE 解析器的脆弱性 (Brittle SSE Parsing)**：
    -   **现象**：在 [useChatState.ts](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts) 中，解析逻辑假设每个数据块 (chunk) 都是完整的 JSON 行。
    -   **问题**：当网络传输导致 JSON 字符串被切断（跨 chunk）或多字节字符（如中文）被截断时，`JSON.parse` 会抛出异常，导致后续的 UI 更新逻辑被跳过。
2.  **多字节字符编码问题**：
    -   直接解码单个 chunk 可能会导致字符截断。
3.  **渲染性能瓶颈 (Rendering Bottleneck)**：
    -   **现象**：在 [useMermaid.ts](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useMermaid.ts) 中，防抖定时器是局部作用域的。
    -   **问题**：高频流式输出触发了大量并发的 Mermaid 渲染尝试，抢占了浏览器主线程，导致 UI 响应迟缓甚至冻结。

### 8.2 修复方案 (Solutions)

1.  **行缓冲区模式 (Line Buffer Pattern)**：
    -   引入 `lineRemainder` 变量缓存不完整的行。
    -   使用 `decoder.decode(value, { stream: true })` 保持解码器状态，处理跨块字符。
2.  **渲染任务调度优化**：
    -   将 Mermaid 渲染定时器提升至 Hook 作用域，确保每次新请求都会取消前一个挂起的渲染任务，实现真正的单任务调度。

### 8.3 经验教训 (Lessons Learned)

-   **流式系统的鲁棒性**：在处理流式数据时，**绝不能假设数据块的边界即是逻辑边界**。必须实现健壮的缓冲区逻辑来应对分片。
-   **渲染节流 (Throttling)**：对于复杂的异步渲染（如 Mermaid, KaTeX），必须有严格的并发控制，防止由于“生产者（API）”速度远快于“消费者（UI 渲染）”而导致的系统崩溃。

---
**更新记录**: 全能设计模式教练
**更新日期**: 2026-02-28
**最新状态**: 已修复前端流式解析瓶颈 (Frontend Stream Parsing Fixed)
