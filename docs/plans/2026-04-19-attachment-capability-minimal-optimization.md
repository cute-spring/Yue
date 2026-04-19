# 聊天附件能力提示与模型能力表达最小化优化建议

## 1. 文档目的

本文档聚焦于当前聊天附件能力中的一个非常必要、但必须严格控制范围的优化主题：

- 让用户看到的“模型能力提示”更准确
- 让“哪些文件能上传、哪些能力能理解”表达更清晰
- 避免把 `图片视觉能力` 和 `PDF/Excel/CSV 附件能力` 混为一谈

本文档**不扩展范围**到以下主题：

- 不引入 OCR
- 不新增 Word / ZIP / 任意二进制文件支持
- 不做 Phase 3 的“模型原生文档理解”扩展
- 不做复杂的模型自动切换
- 不重做上传链路或聊天协议

目标是：在当前已具备的附件上传基础上，用最小改动消除最容易误导用户的认知偏差。

---

## 2. 已完成状态

截至当前，本文档中定义的 4 项最小优化已经全部落地完成，且保持在原定范围内，没有扩展到 Phase 3：

1. 已将视觉提示触发条件从“附件总数”收敛为“图片数量”
2. 已将视觉提示文案改为“只针对图片”的明确表达
3. 已在输入区附件预览区域增加轻量的附件构成提示
4. 已在当前模型状态区域增加轻量能力标签 `Vision / Text Only`

本轮实际落点集中在以下文件：

- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)
- [frontend/src/components/ChatInput.multimodal.test.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.multimodal.test.tsx)

本轮没有进入以下范围：

- 没有新增 OCR
- 没有变更上传协议或后端聊天契约
- 没有引入模型自动切换
- 没有把 PDF 直接映射为视觉输入

---

## 3. 当前实现事实基线

### 3.1 当前允许上传的文件类型

当前前后端已经统一支持以下上传类型：

- 图片：`png / jpg / jpeg / gif / webp`
- 文档：`pdf / xlsx / xls / csv`

对应实现见：

- [backend/app/api/files.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/files.py)
- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)

这意味着“能上传”与“模型能否直接理解”是两个不同问题。

### 3.2 当前图片如何进入模型

当前只有图片会进入 `images` 通道。

- 前端提交时，图片文件会被转成 `base64` 并进入 `images`
- 后端会用 `MultimodalService` 校验图片
- 若模型具备 `vision` 能力，则图片会作为 `ImageUrl` 注入模型输入

对应实现见：

- [frontend/src/hooks/chat/chatSubmission.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/chat/chatSubmission.ts)
- [backend/app/services/multimodal_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/multimodal_service.py)
- [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

结论：

- 图片理解依赖 `vision` 能力
- 这条规则是当前系统中真实成立的

### 3.3 当前 PDF / Excel / CSV 如何进入系统

当前 `pdf / xlsx / xls / csv` 会作为通用附件上传并持久化为 `attachments` 元数据，但**不会直接作为模型的原生多模态输入喂给模型**。

也就是说：

- 它们能上传
- 能在消息中回显
- 能作为“当前消息携带的附件信息”保存下来
- 但它们不是通过 `vision` 通道直接进入模型

对应实现见：

- [backend/app/api/chat.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
- [backend/app/api/chat_schemas.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_schemas.py)
- [frontend/src/types.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/types.ts)

### 3.4 当前模型能力是如何判断的

前端使用 `model_capabilities` 中是否含 `vision` 来判断视觉能力：

- [frontend/src/hooks/useLLMProviders.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useLLMProviders.ts)

后端能力来源优先级为：

1. 显式配置的 `capabilities`
2. Provider 原生返回的能力
3. 基于模型名的启发式推断

对应实现见：

- [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py)
- [backend/app/services/llm/capabilities.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/llm/capabilities.py)

这说明：

- 当前“是否支持视觉”并不是拍脑袋判断
- 但用户界面如何使用这个判断，目前还不够准确

---

## 4. 当前最核心的问题

### 4.1 当前提示把“附件存在”错误等同于“图片存在”

当前前端视觉提示函数：

- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)

现状是：

- `getVisionCapabilityHint()` 接收的是 `attachmentCount`
- 只要附件数量大于 0 且模型不支持视觉，就显示：
  - `当前模型不支持视觉能力，图片请求将被拒绝或降级为纯文本。`

问题在于：

- `attachmentCount` 里既包含图片，也包含 PDF / Excel / CSV
- 用户只上传 PDF，也可能看到“模型不支持视觉能力”的提示
- 这会让用户误以为：
  - PDF 必须用视觉模型才能读
  - Excel/CSV 也属于视觉输入
  - 当前模型完全不能处理文档附件

这三种理解，都是不准确的。

### 4.2 当前提示文案只描述了“图片被拒绝”，没有描述“文档附件不是同一条能力链”

当前提示文案只有一条：

- `当前模型不支持视觉能力，图片请求将被拒绝或降级为纯文本。`

这条话本身对图片是对的，但它少了两个非常关键的信息：

1. 这条提示只针对图片
2. PDF / Excel / CSV 属于附件解析链路，不等同于图片视觉链路

因此，用户会把系统能力理解为“附件能力 = 视觉能力”，这是当前最值得优先修复的认知问题。

### 4.3 当前 UI 没有显式区分“本次上传里有多少图片、多少文档”

当前输入区展示的是统一附件列表，但没有告诉用户：

- 这次有几张图片
- 这次有几个文档
- 哪些会受 `vision` 限制影响
- 哪些只是普通附件上传

因此，即使系统内部已经区分 `imageFiles / nonImageFiles`，用户在界面上仍然看不到这个区别。

---

## 5. 当前能力边界的正确表达

这是当前系统最适合对外表达的事实口径。

### 5.1 可以直接上传的文件

当前可直接上传：

- 图片：`PNG / JPG / JPEG / GIF / WEBP`
- 文档：`PDF / XLSX / XLS / CSV`

### 5.2 哪些内容依赖视觉模型

当前明确依赖视觉模型的是：

- 图片内容理解
- 带图片的问题理解

若模型没有 `vision`：

- 图片请求会被拒绝，或者在开启 fallback 时降级为纯文本模式

### 5.3 哪些内容不应被表述为“依赖视觉模型”

以下内容在当前项目中**不应直接提示为“必须视觉模型”**：

- PDF 上传
- Excel 上传
- CSV 上传

原因不是它们已经百分之百“直接可读”，而是：

- 它们走的是附件链路，不是图片视觉链路
- 当前问题不在上传入口，而在“能力提示准确性”

### 5.4 关于 PDF 的一个必要补充说明

虽然不应把 PDF 一概提示成“必须视觉模型”，但需要保留一个真实边界：

- 如果 PDF 是扫描件、图片页、没有可提取文本，那么后续理解质量可能仍受 OCR/视觉能力影响

但这个属于后续能力边界说明，不应该在当前最小优化中扩写成复杂新逻辑。

当前最小口径应保持为：

- `普通 PDF/表格附件与图片视觉能力不是同一件事`

---

## 6. 非常有必要的最小化优化建议

以下建议都非常必要，而且都可以在当前实现基础上小范围完成，不会扩展到 Phase 3。

### 建议 1：把视觉提示触发条件从“附件总数”改为“图片数量”

状态：已完成

#### 现状

当前视觉提示依据：

- 是否选择了模型
- 模型是否支持视觉
- 附件总数是否大于 0

#### 问题

这会导致：

- 只有 PDF 时也提示视觉不支持
- 只有 Excel/CSV 时也提示视觉不支持

#### 最小改法

把提示触发条件改为：

- `imageFiles.length > 0`

而不是：

- `attachments.length > 0`

#### 为什么这项最必要

这是当前误导最直接、频率最高、影响最大的一个点。

#### 建议落点

- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)

#### 验收标准

- 仅上传 PDF / Excel / CSV 时，不出现视觉能力警告
- 上传至少一张图片且模型无视觉能力时，才出现视觉能力警告

---

### 建议 2：把单条视觉警告文案改成“只针对图片”的明确表述

状态：已完成

#### 现状文案

`当前模型不支持视觉能力，图片请求将被拒绝或降级为纯文本。`

#### 问题

文案没有明确“这条只针对图片”，用户会自然扩展理解到所有附件。

#### 最小改法

建议改为类似以下表达之一：

方案 A：

`当前模型不支持图片理解能力，本次图片不会被分析；PDF/表格附件不受这条提示直接约束。`

方案 B：

`当前模型不支持视觉能力，本提示仅针对图片附件；文档附件走独立附件链路。`

#### 推荐方案

推荐方案 A，因为它更接近用户语言，不要求用户理解“视觉能力”“链路”这类术语。

#### 为什么这项很必要

即使触发条件修正了，用户仍可能在“图片 + PDF 混传”的场景中误解这条提示的覆盖范围。

#### 建议落点

- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)
- 如需保持一致，也可同步 [frontend/src/components/MessageItem.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/MessageItem.tsx) 中的视觉反馈文案

#### 验收标准

- 用户看到提示时，能够明确知道“被限制的是图片，不是所有附件”

---

### 建议 3：在输入区增加一个极轻量的附件构成提示

状态：已完成

#### 现状

当前附件列表能看到文件卡片，但看不到这次上传中的“图片/文档构成”。

#### 最小改法

在附件预览区上方或下方增加一条轻量文字，仅在有附件时显示，例如：

- `已选择 3 个附件：1 张图片，2 个文档`

或者更简洁：

- `附件：图片 1，文档 2`

#### 为什么这项必要

这条提示不是新功能，而是把系统内部已经知道的信息显式告诉用户，能大幅降低误解。

#### 为什么仍然属于最小优化

- 不需要新增接口
- 不需要新增能力判断
- 不需要新增后端数据
- 只利用前端已经存在的 `splitAttachmentsByType()`

#### 建议落点

- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)

#### 验收标准

- 用户在发送前能一眼看出当前上传中是否包含图片
- 用户能理解为什么会出现或不会出现视觉提示

---

### 建议 4：在模型选择区域或当前模型状态处增加一个最小能力标签

状态：已完成

#### 现状

当前模型有没有视觉能力，用户只能通过错误提示或行为结果来感知。

#### 最小改法

对当前已选模型显示一个极轻量标签：

- `Vision`
- 或 `Text Only`

如果需要更稳妥，也可以只在“无 vision 且当前有图片附件”时显示：

- `当前模型：Text Only`

#### 为什么这项必要

只修正文案还不够，用户在上传前仍然不知道模型能力边界。

#### 为什么这项仍然最小

- 不需要新接口
- 不需要新后端
- 不需要新路由
- 只消费已有的 `model_capabilities`

#### 建议落点

- [frontend/src/components/ChatInput.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.tsx)
- 如果视觉上更合适，也可放在 [frontend/src/components/LLMSelector.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/LLMSelector.tsx)

#### 验收标准

- 用户在发送前能感知当前模型是否具备图片理解能力
- 不再只能依赖报错后才知道

---

## 7. 明确不建议现在做的事

为了防止范围扩张，以下优化虽然“可能有价值”，但**当前不建议进入这轮最小优化**：

### 6.1 不建议现在做“模型按附件类型自动切换”

原因：

- 这会引入新的系统行为和不可预测性
- 会扩展到模型路由策略
- 不再属于“提示准确性优化”

### 6.2 不建议现在做“上传时对 PDF 做可读性预检测”

例如检测：

- 是文本 PDF 还是扫描 PDF
- 是否需要 OCR

原因：

- 这是能力增强，不是最小提示优化
- 会引入新的后端计算和额外状态

### 6.3 不建议现在做“附件能力矩阵中心化配置平台”

原因：

- 当前项目已有 `capabilities` 机制
- 这轮目标不是做配置平台，而是先把 UI 表达做正确

### 6.4 不建议现在做“把 PDF 也映射成视觉输入”

原因：

- 这已经进入 Phase 3 的能力扩展
- 也会改变真正的推理路径

---

## 8. 推荐的最小实施顺序

建议按以下顺序落地：

1. 修正视觉提示触发条件  
   从 `attachmentCount` 改为 `imageCount`

2. 修正文案  
   明确提示“只针对图片”

3. 增加附件构成说明  
   例如 `图片 1 / 文档 2`

4. 增加模型能力轻量标签  
   例如 `Vision` 或 `Text Only`

这个顺序的优点：

- 第 1、2 步就能先解决最主要误导
- 第 3、4 步是在不扩 scope 的前提下补足可理解性

当前状态：

- 上述 4 个步骤均已完成
- 实际实现顺序与文档建议顺序一致
- 本轮交付已达到“文档建议全部落地”的状态

---

## 9. 已补充测试覆盖与验收结果

本轮最小优化相关测试已经补充到：

- [frontend/src/components/ChatInput.multimodal.test.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatInput.multimodal.test.tsx)

已覆盖：

### 9.1 视觉提示触发条件测试

- 只有 PDF 时：不显示视觉提示
- 只有 Excel/CSV 时：不显示视觉提示
- 只有图片且模型无 vision 时：显示视觉提示
- 图片 + PDF 混传且模型无 vision 时：显示视觉提示

### 9.2 文案准确性测试

- 视觉提示文案明确包含“仅针对图片”或等价语义

### 9.3 附件构成显示测试

- 仅图片时：显示 `图片 N`
- 仅文档时：显示 `文档 N`
- 混合时：同时显示图片数与文档数

### 9.4 模型能力标识测试

- 有 `vision` 的模型显示对应标签
- 无 `vision` 的模型显示 `Text Only` 或不显示 `Vision`

验收命令：

- `npm run test -- src/components/ChatInput.multimodal.test.tsx`
- `npm run build`

验收结果：

- `ChatInput.multimodal.test.tsx` 通过
- 前端 `build` 通过
- 本轮变更未引入前端类型错误或打包错误

---

## 10. 结论

当前这块最需要优化的，不是上传能力本身，而是**能力提示的准确性**。

当前系统内部已经做对了两件重要事情：

- 把图片和文档附件分成了不同通道
- 把视觉能力判断建立在模型能力元数据之上

但当前 UI 层把这两件事表达得不够清楚，导致用户容易误解成：

- 所有附件都依赖视觉模型
- PDF/Excel 不能在非视觉模型下使用

这正是本轮最小优化应当解决的问题。

最值得做、且最不该拖延的优化是：

1. 视觉提示只在有图片时触发
2. 文案明确只针对图片
3. 输入区显示附件构成
4. 当前模型显示轻量能力标签

这四项改动都非常必要，而且都属于当前 Phase 2.5 范围内的“前端与契约表达加固”，不会提前进入 Phase 3。
