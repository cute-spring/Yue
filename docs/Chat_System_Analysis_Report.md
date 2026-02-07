# Chat System Technical Analysis & Optimization Report

## 1. 核心架构与性能 (Architecture & Performance)

### 1.1 数据库性能瓶颈
- **问题描述**: 目前使用 SQLite (`yue.db`)，且 `messages` 表的 `session_id` 和 `timestamp` 字段**没有建立索引**。
- **状态**: ✅ 已修复
- **解决方案**:
  - 开启 SQLite WAL 模式 (`PRAGMA journal_mode=WAL`) 提升并发。
  - 为 `messages` 表添加 `idx_messages_session_id` 索引。

### 1.2 并发写入风险
- **问题描述**: SQLite 对并发写入支持有限。当前的 `ChatService` 每次请求都新建连接，高并发下可能遇到 `database is locked` 错误。
- **状态**: ✅ 缓解 (通过 WAL 模式)
- **优化建议**: 引入连接池 (Connection Pooling) 或使用 SQLAlchemy 等 ORM 管理会话。

## 2. 功能完整性缺失 (Feature Gaps)

### 2.1 多模态支持缺失
- **问题描述**: 前端 `Chat.tsx` 存在图片上传 UI (`imageAttachments`)，但后端 `chat_service.py` 的 `add_message` 接口仅接收文本内容，数据库缺乏图片存储字段。
- **状态**: ✅ 已修复
- **解决方案**:
  - 后端支持 Base64 图片上传并转存为本地文件。
  - 数据库 `messages` 表新增 `images` 字段存储文件路径。
  - API 支持 `ImageUrl` 格式传递给 LLM。

### 2.2 RAG (知识库) 实现简陋
- **问题描述**: 目前 RAG 依赖硬编码 Prompt (`"可检索目录..."`)，缺乏向量数据库和语义检索支持。
- **潜在后果**: 文档增多后，Prompt 长度迅速超限或被截断，检索准确率极低。
- **优化建议**: 引入向量数据库 (如 Chroma/Qdrant) 和 Embedding 模型，实现语义搜索。

## 3. 错误处理与监控 (Error Handling & Observability)

### 3.1 “吞没”异常 (Swallowed Exceptions)
- **问题描述**: 前端代码 (`Chat.tsx`) 存在大量空的 `catch (e) {}` 块（如复制失败、删除失败时）。
- **状态**: ✅ 已修复
- **解决方案**: 引入全局 `ToastContext`，所有异常操作均通过 Toast 提示用户（Success/Error）。

### 3.2 脆弱的错误判断
- **问题描述**: 后端通过匹配字符串 `"does not support tools"` 来判断是否降级模型。
- **潜在后果**: 依赖底层库特定错误文案，一旦文案变更，降级逻辑将失效导致崩溃。
- **优化建议**: 改为基于模型配置的能力检测 (Capability Check)。

## 4. 上下文与 Token 管理 (Context Management)

### 4.1 “硬截断”策略局限
- **问题描述**: 当前实现的 `truncate` 逻辑达到上限后直接丢弃旧消息。
- **潜在后果**: 上下文丢失，模型对早期对话内容“失忆”。
- **优化建议**: 引入**滚动摘要 (Rolling Summary)** 机制，将旧消息压缩为 Summary 保留。

### 4.2 Token 估算偏差
- **问题描述**: 使用 `len(text) // 3` 进行粗略估算。
- **潜在后果**: 中文或代码内容估算误差大，可能导致 Context Overflow。
- **优化建议**: 集成 `tiktoken` 库进行精确计数。

## 5. 代码质量与维护 (Code Quality)

### 5.1 硬编码问题
- **问题描述**: 存在多处硬编码字符串（如 `"可检索目录"`, 默认模型 `"gpt-4o"` 等）。
- **优化建议**: 提取至配置文件或常量定义。

### 5.2 日志规范
- **问题描述**: 部分服务代码使用 `print` 而非 `logger`。
- **优化建议**: 全面替换为标准 logging，便于生产环境监控。
