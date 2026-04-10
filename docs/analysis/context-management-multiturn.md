# 多轮对话 Context 管理实现分析

本文总结 Yue 当前在多轮对话中的 context 管理实现方式，重点说明它如何保存历史、如何重建上下文、如何做 token 裁剪，以及前后端各自承担什么职责。

## 结论

当前实现不是独立的长期记忆系统，而是以“**会话持久化 + 每轮重建历史 + token 预算裁剪 + prompt 级注入**”为核心。

也就是说：

- 后端负责把历史消息从数据库恢复出来
- 后端负责把历史消息转换成模型可消费的 `message_history`
- 后端负责按 token 预算截断旧消息
- 后端负责把 system prompt、技能 prompt、目录作用域摘要等拼进最终 prompt
- 前端只负责会话状态、消息展示和把 `chat_id` 带回后端

## 1. 会话与消息是如何存的

核心数据模型在 `backend/app/models/chat.py`：

- `Session` 保存会话元信息
- `Message` 保存用户和助手消息
- `ToolCall` 保存工具调用
- `ActionEvent` / `ActionState` 保存技能动作链路

关键字段：

- `session_id` 用来串起同一个会话
- `assistant_turn_id` 用来把某一轮助手消息和工具调用精确绑定
- `run_id` 用来表示一次完整执行

这意味着多轮对话的“上下文”不是只存在内存里，而是可持久化、可回放的。

## 2. 每轮对话是怎么重建 context 的

请求进入 `/api/chat/stream` 时，后端会先读取当前会话，再把历史消息转换为模型输入。

相关流程在：

- `backend/app/api/chat.py`
- `backend/app/services/chat_prompting.py`

具体步骤：

1. 根据 `chat_id` 取出完整会话
2. 读取该会话下的消息历史
3. 将用户消息转换成 `ModelRequest`
4. 将助手消息转换成 `ModelResponse`
5. 把图片消息恢复成 `ImageUrl`
6. 以倒序扫描方式控制历史长度

## 3. 上下文裁剪策略

当前裁剪策略是“**token 预算硬截断**”。

在 `backend/app/services/chat_prompting.py` 中：

- 单条消息最多按 `MAX_SINGLE_MSG_TOKENS = 20000` 估算
- 整个会话上下文最多按 `MAX_CONTEXT_TOKENS = 100000` 估算
- token 估算采用简单启发式：`len(text) // 3`

裁剪方式：

- 从最近消息往前扫描
- 累计 token
- 一旦超限，就直接停止，把更老的消息丢掉

这说明当前策略偏“保留最近轮次”，而不是“压缩老历史”。

## 4. Prompt 是怎么拼出来的

最终 prompt 的组装在 `backend/app/services/chat_prompting.py` 的 `assemble_runtime_prompt()`。

它会把这些内容合并到 system prompt：

- agent 的基础 persona
- 当前选中的 skill prompt
- always skills
- doc scope summary
- 会话摘要块（如果存在）

如果 agent 配置了 `doc_roots`，系统会进一步生成“可检索目录”提示，并在必要时追加 scope summary。

这意味着多轮对话里的 context 不只是“历史消息”，还包括：

- 角色设定
- 技能系统
- 文档检索作用域
- 额外摘要信息

## 5. 前端在 context 管理中的职责

前端主要负责 UI 状态和请求携带，不负责真正的上下文裁剪。

在 `frontend/src/hooks/chat/chatSubmission.ts` 中：

- 新消息提交时会带上 `currentChatId`
- 会把当前会话 ID 写入 `context_id`
- 流式返回时，前端只更新当前消息内容和状态

换句话说，前端知道“属于哪个会话”，但不知道“历史该保留多少”；后者由后端统一决定。

## 6. 当前实现的边界

当前系统已经具备：

- 会话级持久化
- 多轮历史回放
- 按 token 预算裁剪
- prompt 级上下文注入
- 工具调用与助手轮次绑定

但还没有成为完整的“分层记忆系统”：

- 没有 rolling summary 作为主链路
- 没有长期记忆检索
- 没有基于重要性或衰减的记忆管理

路线图里也明确把这些列为待做项，尤其是：

- rolling summary
- 精确 token counting
- short-term / long-term memory

## 7. 涉及的关键文件

- `backend/app/models/chat.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/chat_prompting.py`
- `backend/app/api/chat.py`
- `backend/app/api/chat_stream_runner.py`
- `frontend/src/hooks/chat/chatSubmission.ts`
- `frontend/src/hooks/useChatState.ts`
- `docs/overview/ROADMAP.md`

## 8. 一句话总结

Yue 当前的多轮对话 context 管理，本质上是“**数据库保存整段会话，后端每轮重新构建可用历史，并用 token 预算做硬裁剪，再把运行时 prompt 追加进系统提示**”。

