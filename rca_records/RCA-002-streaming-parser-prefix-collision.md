# RCA-002: 流式解析器前缀冲突导致 UI 更新冻结报告

## 1. 问题描述
用户反馈在流式输出包含特定 HTML/SVG 标签（如 `<title>` 或 `<text>`）的内容时，前端 UI 会在这些标签处异常停止更新，尽管后端 API 仍在持续返回数据。

- **现象**: 响应内容在遇到 `<meta...`、`<title` 或 `stroke-dasharray="..." /> <text` 等位置时停止渲染。
- **范围**: 影响所有包含以 `<t` 开头的 HTML/SVG 标签的长文本生成任务。
- **关键特征**: API 日志显示数据传输完整，但前端 `MessageItem` 显示的内容被截断。

---

## 2. 根因分析 (Root Cause)

经过对前端解析逻辑的深度排查，确定该问题是由 `thoughtParser.ts` 中的**流式状态机前缀碰撞**导致的。

### 2.1 碰撞触发机制
在 [thoughtParser.ts](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/utils/thoughtParser.ts) 中，为了处理 DeepSeek 的思维链（Reasoning Chain），引入了前缀检测逻辑：
```typescript
// 潜在的标签前缀，用于避免在流式传输时内容闪烁
const tagPrefixes = ["<t", "<th", "<thi", "<thin", "<think", "<thou", "<thoug", "<thought"];
```

### 2.2 逻辑死锁 (Deadlock)
当解析器遇到 `<` 字符时，会检查剩余部分是否可能是一个正在传输中的思维标签：
1.  **匹配失败**: 如果内容是 `<title` 或 `<text`，它们都命中了 `tagPrefixes` 中的 `"<t"`。
2.  **状态挂起**: 解析器认为这是一个“尚未传输完成的思维标签”，为了防止错误渲染，它会执行 `break` 退出解析循环。
3.  **累积效应**: 由于前端每次更新都是对**全量累积文本**进行重新解析，一旦文本中包含了 `<title`，解析器每次都会在同一个位置触发 `break`。
4.  **最终表现**: 解析出的 `content` 字段永远停留在了 `<` 之前的位置，导致 UI 停止更新。

---

## 3. 经验教训 (Lessons Learned)

### 3.1 贪婪匹配的风险
在处理流式数据时，基于字符串前缀的“预测性隐藏”逻辑（Anticipatory Hiding）必须非常精确。过于宽泛的前缀（如 `"<t"`）极易与业务内容（HTML 标签）产生冲突。

### 3.2 幂等解析的性能与正确性
前端采用“全量重解析”模式虽然实现简单，但如果解析器内部存在非幂等或带有误判风险的状态机，错误会被无限放大。

---

## 4. 修复方案 (Implementation)

### 4.1 精确前缀匹配 (Precise Prefix Matching)
修改 [thoughtParser.ts](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/utils/thoughtParser.ts)，将原有的宽泛匹配（如 `"<t"`）替换为基于合法思维标签的严格前缀检查：

```typescript
// 仅检查是否为合法思维标签的前缀
const allowedTags = ["<think>", "<thought>", "</think>", "</thought>"];
const isPotentialTag = allowedTags.some(tag => tag.startsWith(remaining.toLowerCase()));
```

**逻辑效果**：
- 如果 `remaining` 是 `"<t"`，它是 `"<think>"` 的前缀 → **拦截**（流式等待）。
- 如果 `remaining` 是 `"<title"`，它不是任何合法标签的前缀 → **放行**（HTML 正常渲染）。

---

## 5. 验证结果 (Verification)

1.  **场景 A (HTML)**: 遇到 `<title>` 标签时，解析器不再因匹配到 `"<t"` 而跳出。
2.  **场景 B (SVG)**: 遇到 `<text>` 标签时，解析器能正确识别其为业务内容，保持渲染更新。
3.  **场景 C (Streaming)**: 当模型确实在输出 `"<thi"` 时，由于它是 `"<think>"` 的合法前缀，系统依然会保持隐藏直到标签闭合，避免了思维链碎片的闪烁。

### 4.2 流式状态感知 (Streaming-Aware Parsing)
在最终方案中，我们引入了 `isStreaming` 标志位。只有在消息处于流式传输状态（`isTyping === true`）时，解析器才会执行“前缀拦截”逻辑。

**改进代码**：
```typescript
// ONLY if we are still streaming. If not streaming, treat as regular text.
if (isStreaming) {
  const isPotentialTag = allowedTags.some(tag => tag.startsWith(remaining.toLowerCase()));
  if (isPotentialTag && i + remaining.length === n) {
    isThinking = true;
    break;
  }
}
```

**方案优势**：
1.  **彻底隔离**: 当消息完成生成后，即使内容中包含 `<title` 等字符串，由于 `isStreaming` 为 `false`，解析器会将其视为普通文本，不再进行截断。
2.  **性能优化**: 前端使用 `createMemo` 缓存解析结果，避免了在不必要的重渲染中重复解析长文本。
3.  **多模型兼容**: 增加了对 `[thought]` 和 `[thinking]` 等不同模型思维标签格式的支持。

---

## 5. 结论
本次故障的最终解决思路是：**将解析逻辑从“静态文本处理”演进为“状态感知处理”**。在处理 AI 生成内容时，解析器不应仅关注文本内容本身，还必须结合当前消息的生命周期状态（流式 vs 静态）来决定解析策略。
