**上传文件支持计划（前端 + 后端 + 存储）**

简要目标：
- 让用户能够从聊天输入框上传任意（受限类型）文件，并在聊天消息中引用与预览。优先支持 images/pdf/docx/xlsx/zip。后端提供稳健的 multipart 上传 API，并将文件保存到现有 uploads 目录，返回可公开访问的 `/files/...` URL 或文件 ID。

范围（MVP）：
- 后端新增 POST `/api/files` 接口，接收 `multipart/form-data`，返回文件元数据（id/filename/url/mime/size）。
- 前端在 `ChatInput` 增加通用文件选择控件并显示待上传文件列表。
- 前端提交消息前先上传文件（使用 `FormData`），将返回的 URL/ID 列表随 chat 请求发送（`attachments` 字段）。
- 后端在 `chat_service.add_message` 中保存 `attachments` 引用（临时可用 message.images 或并行字段），并通过 `/files` 静态挂载提供文件下载。
- 消息展示组件渲染附件链接与基本预览（图片内嵌、PDF 预览/下载）。

详细里程碑（分阶段）：

Phase 1 — POC（半天 — 1 天）
- 新增后端 API `POST /api/files`（无鉴权、仅大小/类型限制）
- 前端实现上传 POC：用户选择文件 -> 上传 `/api/files` -> 在消息列表显示返回的 URL（不改 DB，消息内容临时包含 attachments）
- 验证静态 `/files` 能直接访问上传的文件

Phase 2 — 稳健实现（1–2 天）
- 添加 DB migration：`messages.attachments`（JSON text）或扩展 `images` 字段为 attachments 结构（含 mime/size/display_name/id/url）
- 更新 `chat_service.add_message` 将 attachments 持久化到 DB
- 前端在 `useChatState.handleSubmit` 中先上传文件、再发送 chat 请求（包含 attachments）
- 更新消息渲染（`MessageItem`）：文件图标、文件名、大小、下载/预览按钮

Phase 3 — 质量与安全（1–2 天）
- 服务端实施严格校验：最大文件大小、白名单 MIME/type、单次上传数量限制
- 添加速率限制、鉴权检查（如需要）和审计日志
- 添加过期/垃圾文件清理策略（cron job 或后台任务）
- 可选：签名 URL 支持（短期访问凭证）和 CDN 分发

Phase 4 — 测试与发布（0.5–1 天）
- 后端单元测试：上传接口、静态文件可访问、DB 持久化
- 前端 e2e：上传图片/PDF，确认聊天消息中出现可访问链接与预览
- 文档：更新 README、迁移说明与用户说明

关键修改文件（定位清单）：
- 前端
  - `frontend/src/components/ChatInput.tsx` — 添加文件 input 和上传 UX
  - `frontend/src/hooks/useChatState.ts` — 实现 `uploadFiles()` 与在 `handleSubmit` 前上传并把 attachments 添加到请求体
  - `frontend/src/components/MessageItem.tsx` / `MessageList.tsx` — 渲染附件
  - e2e 测试：`frontend/e2e/multimodal-image-chat.spec.ts`（新增文件上传场景）

- 后端
  - 新增路由文件：`backend/app/api/files.py`（POST `/api/files`）
  - 复用/扩展：`backend/app/utils/image_handler.py`（提取通用保存逻辑）
  - 持久化层：`backend/app/models/chat.py`（新增 `attachments` 列）
  - 服务层：`backend/app/services/chat_service.py`（保存 attachments）
  - 配置/启动：`backend/app/main.py`（已挂载 `/files`，确认 uploads 目录权限）

数据模型建议（attachments JSON 示例）：
[
  {
    "id": "<uuid>",
    "display_name": "report.pdf",
    "url": "/files/<uuid>.pdf",
    "mime": "application/pdf",
    "size": 234234
  }
]

安全与运维要点（必须考虑）：
- 服务端强制大小上限（例如默认 20MB，可配置）和白名单 MIME
- 身份验证（对受限部署）与速率限制防止滥用
- 文件名/路径规范化以避免目录遍历；只通过 `/files` 静态路径暴露
- 日志和清理策略（定期清理临时/过期文件）

回滚与兼容策略：
- 先实现 POC：不改 DB，仅返回 URL 并在前端临时引用。确认一切后再做 DB migration。这样可快速回滚（前端切回 base64 行为）。

估算与优先级：
- POC：4–8 小时（高优先级）
- 完整实现（含 DB、展示、测试）：1.5–3 人天（中优先级）
- 安全/运维增强：0.5–2 人天（视生产要求）

下一步（我可以代劳）：
- 立刻创建 `backend/app/api/files.py` 的 POC 实现与对应前端 POC（`ChatInput` + `useChatState.uploadFiles`），并运行基本测试。请确认是否现在开始 POC 实施？

