# Chat 附件上传与 Excel/PDF 可读能力落实方案

## 1. 背景与目标

本方案用于落实聊天记录中的“附件上传”能力，覆盖：

- 在当前聊天记录中上传文件
- 支持点击上传
- 支持粘贴上传
- 首期重点支持 `PDF / XLSX / XLS / CSV`
- 附件随消息持久化并可回看
- Agent 能读取当前消息中的 Excel/PDF 附件并参与回答

本方案采用我当前最推荐的推进路径：

1. 先把“通用附件模型”做对
2. 再把“上传链路”做稳
3. 再把“消息展示与历史持久化”补齐
4. 最后把“Excel/PDF 可读能力”打通

不建议继续沿用“图片特例”思路扩展，因为当前实现已经明显表现出图片链路与通用文件链路分离的问题。

---

## 2. 当前基线与关键观察

### 2.1 前端当前只支持图片附件

- 输入区的数据模型只有 `imageAttachments`，没有通用 `fileAttachments`，见 `frontend/src/components/ChatInput.tsx:43-47`
- 提交前仅把图片转 base64 并随 `images` 字段发送，见 `frontend/src/hooks/chat/chatSubmission.ts:88-145`
- 粘贴逻辑当前只提取图片文件，见 `frontend/src/components/ChatInput.tsx:117-127`
- 用户消息渲染当前也只显示 `images`，见 `frontend/src/components/MessageItem.tsx:486-495`

结论：前端已有“附件交互壳子”，但实现仍然是“图片专用”。

### 2.2 后端聊天协议当前只有图片字段

- 聊天请求模型只有 `images`，没有 `attachments`，见 `backend/app/api/chat_schemas.py:7-21`
- 聊天流接口在入站时只校验图片并落盘图片，见 `backend/app/api/chat.py:454-481`
- `chat_service.add_message()` 当前只接收 `images` 参数并序列化到消息表，见 `backend/app/services/chat_service.py:530-589`
- `messages` 表只有 `images` 列，没有附件列，见 `backend/app/models/chat.py:25-54`

结论：后端当前的数据契约和存储结构都不支持通用文件附件。

### 2.3 上传目录与静态访问能力已经存在

- 服务已挂载 `/files` 静态目录，见 `backend/app/main.py:98-107`
- 图片保存已统一写入 `YUE_DATA_DIR/uploads`，见 `backend/app/utils/image_handler.py:9-46`

结论：文件静态分发基础已经具备，不需要从零设计文件服务。

### 2.4 Excel/PDF 处理能力已存在，但未与聊天附件打通

- Excel 服务已支持 profile/read/query，仓库已有大量测试覆盖，见 `backend/tests/test_excel_service.py`
- PDF 检索与页面处理能力已存在于 `backend/app/services/doc_retrieval.py`
- PDF 页面渲染结果会写入 `/files`，但写入目录仍使用旧路径 `backend/data/uploads`，见 `backend/app/services/doc_retrieval.py:786-792`
- 聊天历史回放构建时只会把 `message.images` 注入多模态上下文，见 `backend/app/services/chat_prompting.py:144-152`

结论：文档能力本身不缺，真正缺的是“附件身份模型 + 安全路径接入 + 提示词/工具调用衔接”。

---

## 3. 需求拆解

### 3.1 本期业务目标

用户在聊天记录中可以：

- 点击上传 PDF/Excel/CSV
- 通过粘贴上传图片，条件允许时支持粘贴文件
- 发送后在消息里看到附件卡片
- 后续重新打开聊天历史时仍能看到附件
- 在提问时让 Agent 基于附件内容回答问题

### 3.2 本期非目标

- 首期不做 Word/ZIP/任意二进制深度理解
- 首期不做附件跨会话“资料库”复用
- 首期不做 OCR 流程
- 首期不做云存储/S3
- 首期不做复杂权限体系或签名下载 URL

### 3.3 推荐的 MVP 范围

MVP 仅覆盖以下格式与能力：

- `image/*`
- `application/pdf`
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `application/vnd.ms-excel`
- `text/csv`

MVP 目标是“上传稳定、消息可见、Excel/PDF 可读”，而不是“一次性做成全量文件平台”。

---

## 4. ADR：推荐决策

### 4.1 决策

采用“通用附件模型 + 独立上传接口 + 消息持久化引用 + 工具按附件解析”的方案。

### 4.2 决策驱动因素

- 当前图片链路是特例实现，继续扩展会让 `images` 成为坏的兼容层
- `/files` 已存在，适合复用为本地文件分发出口
- Excel/PDF 服务已存在，优先打通，而不是重新发明文件理解逻辑
- 未来若接入 Storage Provider 抽象层，该模型也更容易迁移

### 4.3 备选方案与取舍

#### 方案 A：继续复用 `images` 字段，给 PDF/Excel 也塞进去

优点：

- 变更少
- 可以更快做出表面可用版本

缺点：

- 语义错误，后续维护成本高
- 前后端类型会越来越混乱
- Prompt、回放、渲染、测试都要继续堆分支

结论：不推荐。

#### 方案 B：新增通用 `attachments` 模型，但上传仍走 base64 聊天请求

优点：

- 不必额外设计文件上传接口

缺点：

- PDF/Excel 不适合塞进聊天流请求体
- 大文件会显著放大请求体和日志风险
- 不利于预上传校验、失败重试和审计

结论：不推荐。

#### 方案 C：独立文件上传 API + 消息挂附件引用

优点：

- 结构清晰
- 与图片、PDF、Excel 可统一治理
- 更利于大小限制、类型校验、失败重试、后续接入 S3

缺点：

- 需要新增接口和消息模型
- 实施步骤比方案 A 更完整

结论：推荐。

---

## 5. 目标架构

### 5.1 数据模型

新增消息级 `attachments` 字段，结构建议如下：

```json
[
  {
    "id": "att_01H...",
    "kind": "file",
    "display_name": "quarterly-report.pdf",
    "storage_path": "uploads/chat/2026/04/19/att_01H....pdf",
    "url": "/files/chat/2026/04/19/att_01H....pdf",
    "mime_type": "application/pdf",
    "size_bytes": 2483921,
    "extension": ".pdf",
    "source": "upload",
    "status": "ready"
  }
]
```

说明：

- `images` 字段短期保留用于兼容旧消息
- 新消息统一写入 `attachments`
- 图片在新模型中也作为附件保存，但前端渲染可继续保持图片体验

### 5.2 API 设计

新增接口：

- `POST /api/files`
  - `multipart/form-data`
  - 支持多文件
  - 返回附件元数据数组

聊天接口调整：

- `POST /api/chat/stream`
  - 新增 `attachments`
  - `images` 保留兼容，但新前端不再依赖其承载 PDF/Excel

### 5.3 存储策略

统一存储根：

- `YUE_DATA_DIR/uploads`

建议目录结构：

```text
uploads/
  chat/
    2026/
      04/
        19/
          att_xxx.pdf
          att_xxx.xlsx
```

这样做的原因：

- 避免所有文件堆在单目录
- 便于未来做清理和迁移
- 与静态 `/files` 挂载兼容

### 5.4 Agent 可读策略

推荐第一版采用“显式附件注入”而不是“自动全文塞进上下文”：

- 用户消息带附件元数据进入运行时
- Prompt 层说明“本轮有可用附件”
- 当用户提问涉及 Excel/PDF 时，优先由现有工具读取附件路径
- 不在模型输入中直接内联整份 PDF/Excel 原文

这样能避免上下文爆炸，也能复用现有工具与引用能力。

---

## 6. 实施计划

### Phase 0：契约与存储统一

目标：先把“附件是什么”定义清楚。

实施项：

1. 在前端类型 `frontend/src/types.ts` 新增 `Attachment` 类型，并把 `Message` 扩展为 `attachments?: Attachment[]`
2. 在后端请求模型 `backend/app/api/chat_schemas.py` 新增 `attachments`
3. 在后端消息表 `backend/app/models/chat.py` 新增 `attachments` 列
4. 在 `backend/app/services/chat_service.py` 为 `add_message()` 增加 `attachments` 参数
5. 保持 `images` 兼容读取，避免旧历史记录失效

验收标准：

- 新旧消息都能正常读取
- 新消息可携带附件元数据
- 历史接口返回的消息结构稳定

### Phase 1：独立文件上传 API

目标：把“上传动作”从聊天流中剥离出来。

实施项：

1. 新增 `backend/app/api/files.py`
2. 支持 `multipart/form-data`
3. 服务端校验：
   - MIME 白名单
   - 扩展名白名单
   - 单文件大小限制
   - 单次上传数量限制
4. 统一使用 `YUE_DATA_DIR/uploads`
5. 返回规范化附件元数据
6. 在 `backend/app/main.py` 注册 `files` 路由

验收标准：

- 可上传 PDF/Excel/CSV/图片
- 非法类型和超限文件会返回稳定错误码
- 上传后可通过 `/files/...` 访问

### Phase 2：前端上传入口与消息展示

目标：让用户真正用起来。

实施项：

1. 在 `frontend/src/components/ChatInput.tsx` 中新增通用文件附件状态
2. 点击上传支持图片、PDF、Excel、CSV
3. 粘贴能力策略：
   - 第一版稳定支持图片粘贴
   - 文件粘贴做能力探测，能取到文件则接入，取不到则不承诺
4. 在提交前先调用 `/api/files`
5. 聊天提交时传 `attachments`
6. 在 `frontend/src/components/MessageItem.tsx` 渲染附件卡片：
   - 图片缩略图
   - PDF/Excel 文件卡片
   - 文件名 / 大小 / 下载入口

验收标准：

- 选择文件后可见待发送附件
- 上传成功后消息中能看到附件
- 刷新页面后历史消息仍能回显附件

### Phase 3：聊天运行时与附件可读能力

目标：让 Agent 真正会用附件。

实施项：

1. 在聊天运行时增加附件快照与追踪
2. 在提示词构建层区分：
   - 图片附件
   - PDF 附件
   - Excel/CSV 附件
3. 为当前消息的附件生成可供工具调用的受控路径引用
4. 优先复用：
   - `backend/app/services/excel_service.py`
   - `backend/app/services/doc_retrieval.py`
5. 对首轮能力定义：
   - PDF：目录、页码文本、关键字页定位
   - Excel：profile/read/query

验收标准：

- 上传 PDF 后，用户可直接提问“总结这份 PDF”
- 上传 Excel 后，用户可直接提问“分析这个表格”
- 工具调用链路能在 trace 中看到附件摘要

### Phase 4：安全、治理与清理

目标：把功能从“能跑”提升到“可上线”。

实施项：

1. 把上传目录与文档访问控制统一纳入同一策略
2. 增加敏感扩展名 denylist
3. 增加结构化审计日志
4. 增加垃圾文件清理策略
5. 修正 `doc_retrieval.py` 中 PDF 渲染仍写旧目录的问题

验收标准：

- 上传目录不会绕过文档访问控制
- 删除会话后的清理策略有定义
- 日志可追踪上传、引用、拒绝原因

---

## 7. 文件级落实清单

### 7.1 前端

- `frontend/src/types.ts`
  - 新增 `Attachment` 类型
  - 扩展 `Message`

- `frontend/src/components/ChatInput.tsx`
  - 从 `imageAttachments` 升级为通用附件状态
  - 复用现有按钮和粘贴入口
  - 当前图片专用逻辑位置见 `:43-47`, `:117-127`, `:197-214`

- `frontend/src/hooks/chat/chatSubmission.ts`
  - 当前图片 base64 提交流程见 `:88-145`
  - 需改为“先上传，再提交聊天”

- `frontend/src/components/MessageItem.tsx`
  - 当前仅渲染 `images`，见 `:486-495`
  - 需改为附件卡片渲染

### 7.2 后端

- `backend/app/api/chat_schemas.py`
  - 当前只有 `images`，见 `:7-21`
  - 需新增 `attachments`

- `backend/app/api/chat.py`
  - 当前流接口只处理图片，见 `:454-481`
  - 需增加附件元数据入站与持久化

- `backend/app/models/chat.py`
  - 当前 `messages` 只有 `images`，见 `:28-33`
  - 需新增 `attachments`

- `backend/app/services/chat_service.py`
  - 当前 `add_message()` 只写 `images`，见 `:530-589`
  - 需扩展为附件持久化

- `backend/app/utils/image_handler.py`
  - 当前只负责 base64 图片存取，见 `:9-46`
  - 建议抽象为更通用的上传存储工具或新增 `file_storage.py`

- `backend/app/main.py`
  - 当前已挂载 `/files`，见 `:98-107`
  - 需新增 `files` router 注册

- `backend/app/services/chat_prompting.py`
  - 当前历史构造只识别 `message.images`，见 `:144-152`
  - 需新增附件类型分流逻辑

- `backend/app/services/doc_retrieval.py`
  - 当前 PDF 渲染还写旧目录 `backend/data/uploads`，见 `:786-792`
  - 需统一到 `YUE_DATA_DIR/uploads`

---

## 8. 安全与前期准备项

这是本需求最应该提前准备的部分。

### 8.1 必须先定的策略

1. 首期格式白名单
2. 单文件大小限制
3. 单次最大文件数
4. 文件保留策略
5. 会话删除时是否同步清理附件

建议默认值：

- 单文件上限：20MB
- 单次最多：5 个文件
- 首批白名单：图片、PDF、XLSX、XLS、CSV

### 8.2 访问控制统一

当前文档访问控制已有独立规划，见 `docs/plans/document_access_control_enhancement_plan_20260323.md`。  
本次附件能力必须与该策略对齐，避免出现：

- 文件传上去了但工具读不到
- 或者工具能绕过路径约束读到不该读的文件

建议做法：

- 上传目录作为受控 allow root 的一部分
- 所有附件解析均通过统一路径解析函数进入
- 不直接把物理绝对路径暴露给前端或模型

### 8.3 粘贴上传的产品边界

建议在 PRD 和交付说明里明确：

- 图片粘贴：MVP 必做
- 文件粘贴：浏览器能力允许时支持，不作为首版核心承诺

原因：

- 浏览器对剪贴板文件的支持不稳定
- Excel/PDF 的复制粘贴来源差异很大
- 过早承诺会带来大量兼容性成本

---

## 9. 测试与验证计划

### 9.1 单元测试

- 上传接口校验
- 附件元数据序列化/反序列化
- 大小限制与类型限制
- 会话消息附件持久化

建议新增：

- `backend/tests/test_file_upload_api.py`
- `backend/tests/test_chat_attachment_persistence.py`

### 9.2 集成测试

- 上传 PDF 后创建消息并回读历史
- 上传 Excel 后创建消息并触发工具读取
- 历史消息中的附件在回放时结构不丢失

### 9.3 前端测试

- `ChatInput` 选择 PDF/Excel
- 上传失败提示
- 附件卡片渲染
- 历史聊天回显

### 9.4 E2E 测试

建议新增场景：

1. 上传 PDF 并发送消息
2. 上传 Excel 并发送消息
3. 粘贴图片并发送消息
4. 刷新后验证附件仍存在

### 9.5 手工验收脚本

1. 新建聊天
2. 上传一个 PDF
3. 发送“请总结这个 PDF 的核心观点”
4. 上传一个 Excel
5. 发送“请统计表格里每个分类的总数”
6. 刷新页面
7. 重新打开会话并确认附件仍可见

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 继续沿用 `images` 扩展 | 数据模型失控 | 强制引入 `attachments` |
| 上传目录与文档访问控制割裂 | Agent 读不到附件或越权读取 | 上传目录纳入统一路径策略 |
| PDF/Excel 直接塞入聊天请求 | 请求体膨胀、失败重试困难 | 独立上传 API |
| 粘贴文件兼容性差 | 用户预期落差 | 首版只承诺图片粘贴稳定 |
| 历史兼容性破坏 | 旧记录无法显示 | 保留 `images` 兼容读取 |
| 两套上传目录并存 | 文件散落、清理困难 | 统一 `YUE_DATA_DIR/uploads` 并修复旧路径写入 |

---

## 11. 验收标准

- [ ] 用户可在聊天输入区点击上传 PDF/Excel/CSV/图片
- [ ] 用户可通过粘贴稳定上传图片
- [ ] 消息发送后可看到附件卡片
- [ ] 刷新后聊天历史仍能回显附件
- [ ] 后端消息模型支持 `attachments`
- [ ] 上传接口具备类型、大小、数量校验
- [ ] Agent 可读取当前消息中的 PDF 与 Excel 附件
- [ ] 上传目录与文档访问控制策略统一
- [ ] 旧图片消息不回归

---

## 12. 建议排期

### Sprint 1

- Phase 0
- Phase 1

交付结果：

- 通用附件模型
- 独立上传接口
- 静态访问与元数据回传

### Sprint 2

- Phase 2
- Phase 3

交付结果：

- 前端上传体验
- 历史展示
- Excel/PDF 可读

### Sprint 3

- Phase 4
- 测试补全
- 发布文档

交付结果：

- 安全治理
- 清理策略
- 上线准备

---

## 13. 推荐执行顺序总结

如果按我的专业建议，最稳的执行顺序是：

1. 定义 `attachments` 模型，不再把 PDF/Excel 塞进 `images`
2. 新增独立上传接口 `/api/files`
3. 前端改为先上传、再发消息
4. 消息展示改为附件卡片
5. 聊天运行时接入附件元数据
6. 复用现有 Excel/PDF 服务读取附件
7. 最后统一访问控制、清理策略和测试

这条路径的优点是：

- 能快速做出用户可感知结果
- 不会把现有图片链路越改越乱
- 与后续文件存储抽象层、文档访问控制重构方向一致

---

## 14. 相关文档

- [upload_file_integration_plan_20260324.md](./upload_file_integration_plan_20260324.md)
- [document_access_control_enhancement_plan_20260323.md](./document_access_control_enhancement_plan_20260323.md)
- [MS_EXCEL_SUPPORT_PLAN.md](./MS_EXCEL_SUPPORT_PLAN.md)
- [PDF_BUILTIN_TOOLS_HIGH_ROI.md](./PDF_BUILTIN_TOOLS_HIGH_ROI.md)
- [File_Management_Improvement_Review.md](./File_Management_Improvement_Review.md)
