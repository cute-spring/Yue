# Chat Trace Inspector 用户使用说明

这份说明面向团队成员，帮助大家快速开启并使用 `Trace Inspector`，用于查看历史 chat 的请求与工具调用过程。

## 1. 这个功能是做什么的

`Trace Inspector` 是一个只读的历史调试面板，用来查看：

- 最近一次请求实际发送给大模型的内容
- 每一次工具调用的完整链路
- 工具输入、输出、耗时、错误信息
- 父子调用关系和调用顺序

它不会修改聊天记录，也不会执行 retry / re-run / edit。

## 2. 怎么打开

默认情况下，这个功能是隐藏的，需要在系统设置里开启。

进入：

- `System Configuration`
- `General`
- `Feature Flags`

然后按需要打开：

- `Trace Inspector UI`
  - 对应后端开关：`chat_trace_ui_enabled`
  - 作用：显示聊天页里的 `Trace Inspector` 入口
- `Raw Trace Access`
  - 对应后端开关：`chat_trace_raw_enabled`
  - 作用：允许在面板里切到 `Raw` 模式

建议顺序：

1. 先打开 `Trace Inspector UI`
2. 需要更深入调试时，再打开 `Raw Trace Access`

## 3. 怎么使用

### 查看摘要信息

1. 打开一个已有历史记录的 chat
2. 点击聊天页顶部的 `Trace Inspector`
3. 在 drawer 里查看 `Summary` 模式
4. 重点看这些内容：
   - request snapshot
   - message history
   - attachments
   - tool trace list
   - trace tree

### 查看原始信息

如果已经开启 `Raw Trace Access`：

1. 在 `Trace Inspector` 里切换到 `Raw`
2. 查看更完整的原始 payload
3. 重点看：
   - `system_prompt`
   - tool 输入参数
   - tool 输出结果
   - 错误详情

## 4. 适合什么场景

- 分析为什么模型收到的最终 prompt 和预期不同
- 排查工具调用链条是否正确
- 检查某个工具为什么报错或返回异常
- 对比 summary 和 raw 内容，做 prompt 调优

## 5. 不适合什么场景

- 不适合做调试操作控制台
- 不支持 retry / re-run / patch
- 不会自动修复或重放历史请求

## 6. 常见问题

### 看不到入口按钮

检查 `chat_trace_ui_enabled` 是否已经打开，并刷新页面。

### 只有 Summary，没有 Raw 按钮

检查 `chat_trace_raw_enabled` 是否已经打开。

### 提示没有 trace summary

表示当前 chat 还没有保存对应的 trace 数据，或者该历史会话没有记录到可展示的工具调用。

### 打开 drawer 后影响了正常聊天

理论上不会。如果出现这种情况，请先关闭两个 feature flags：

- `chat_trace_ui_enabled=false`
- `chat_trace_raw_enabled=false`

然后回报给开发或运维排查。

## 7. 相关文档

- [Chat Trace Inspection Release Checklist](./2026-04-03-chat-trace-inspection-release-checklist.md)
- [Chat Trace Inspection Delivery Summary](./2026-04-03-chat-trace-delivery-summary.md)
- [Chat Trace Release Announcement](./2026-04-03-chat-trace-release-announcement.md)
