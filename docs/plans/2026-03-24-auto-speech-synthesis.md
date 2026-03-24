# AI 回答自动朗读功能实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI 回答完成后自动调用浏览器语音合成 API 朗读回答内容，提供用户友好的听觉体验。

**Architecture:** 采用分层架构：底层为可复用的语音合成 Hook，中间层为设置管理，上层为 Chat 页面的自动触发逻辑。功能主要在前端实现，利用浏览器原生 Web Speech API。设置持久化优先沿用现有 `/api/config/preferences` 流程，避免与现有偏好系统分叉；如果后端暂不接受新增字段，则需要在计划中明确一个独立的 client-side 配置存储方案。

**Tech Stack:** 
- Web Speech API (SpeechSynthesis)
- SolidJS Hooks
- 现有偏好设置 API / 前端状态管理
- 现有设置页面架构

---

## 文件结构

### 新增文件
- `frontend/src/hooks/useSpeechSynthesis.ts` - 语音合成核心 Hook
- `frontend/src/components/SpeechControl.tsx` - 朗读控制按钮组件
- `frontend/src/context/PreferencesContext.tsx` - 偏好设置共享上下文

### 修改文件
- `frontend/src/pages/settings/components/GeneralSettingsTab.tsx` - 添加朗读开关
- `frontend/src/hooks/useChatState.ts` - 集成自动朗读触发
- `frontend/src/components/MessageItem.tsx` - 添加手动朗读按钮
- `frontend/src/pages/settings/types.ts` - 扩展设置类型定义
- `frontend/src/pages/settings/useSettingsData.ts` - 读写偏好设置
- `frontend/src/pages/Settings.tsx` - 接入共享偏好设置
- `frontend/src/index.tsx` - 挂载偏好设置 Provider

---

## 功能设计

### 1. 核心能力

#### 1.1 语音合成 Hook (useSpeechSynthesis)
**职责：** 封装浏览器 SpeechSynthesis API，提供声明式调用接口

**核心功能：**
- 检查浏览器兼容性
- 获取可用语音列表
- 控制朗读（开始/暂停/恢复/停止）
- 监听朗读事件（开始/结束/错误）
- 支持语速、音调、音量调节

**状态管理：**
- `isSpeaking` - 是否正在朗读
- `isPaused` - 是否暂停
- `supported` - 浏览器是否支持
- `voices` - 可用语音列表
- `currentVoice` - 当前选中的语音

**对外接口：**
- `speak(text: string, options?: SpeechOptions)` - 开始朗读
- `pause()` - 暂停朗读
- `resume()` - 恢复朗读
- `stop()` - 停止朗读
- `setVoice(voice: SpeechSynthesisVoice)` - 切换语音

#### 1.2 用户设置
**设置项：**
- `auto_speech_enabled` - 是否启用自动朗读（默认关闭）
- `speech_voice` - 首选语音（默认浏览器默认）
- `speech_rate` - 语速（默认 1.0，范围 0.5-2.0）
- `speech_volume` - 音量（默认 1.0，范围 0-1）

**存储方式：**
- 优先扩展现有 `/api/config/preferences` 读写链路
- 设置页面与聊天页共享同一份偏好来源，避免多处写入产生漂移
- 若确实必须做纯前端存储，则要在计划中单独补充同步、默认值和迁移策略

#### 1.3 自动触发逻辑
**触发时机：**
- AI 流式响应成功结束后，且确认不是用户中止、网络错误或解析错误
- 仅当用户开启了自动朗读开关
- 仅朗读最后一条 assistant 消息

**跳过条件：**
- 消息内容为空
- 消息是错误信息
- 浏览器不支持语音合成
- 用户正在朗读其他内容

#### 1.4 手动控制
**触发方式：**
- 每条 assistant 消息底部添加朗读按钮
- 点击按钮后朗读该条消息内容，再次点击则停止该条消息朗读
- 该按钮同时承担“播放 / 停止”两种状态切换，不新增单独的停止按钮

**按钮状态：**
- 默认显示喇叭图标
- 正在朗读时显示暂停图标
- 暂停时显示播放图标

---

## 任务分解

### Task 1: 语音合成核心 Hook

**Files:**
- Create: `frontend/src/hooks/useSpeechSynthesis.ts`
- Test: `frontend/src/hooks/useSpeechSynthesis.test.ts`

- [ ] **Step 1: 编写 Hook 基础结构**
  - 定义 TypeScript 类型（SpeechOptions, SpeechState）
  - 创建 Hook 函数签名
  - 初始化状态信号

- [ ] **Step 2: 实现浏览器兼容性检测**
  - 检查 `window.speechSynthesis` 是否存在
  - 初始化 `supported` 状态

- [ ] **Step 3: 实现语音列表加载**
  - 监听 `voiceschanged` 事件
  - 获取并缓存可用语音列表

- [ ] **Step 4: 实现核心朗读方法**
  - `speak()` 方法创建 SpeechSynthesisUtterance
  - 设置文本、语音、语速、音量
  - 绑定事件处理器（start/end/error）

- [ ] **Step 5: 实现控制方法**
  - `pause()` / `resume()` / `stop()`
  - 更新状态

- [ ] **Step 6: 编写单元测试**
  - 测试浏览器兼容性检测
  - 测试状态变化
  - Mock SpeechSynthesis API

- [ ] **Step 7: 提交**
```bash
git add frontend/src/hooks/useSpeechSynthesis.ts frontend/src/hooks/useSpeechSynthesis.test.ts
git commit -m "feat: add speech synthesis hook"
```

---

### Task 2: 设置系统集成

**Files:**
- Modify: `frontend/src/pages/settings/types.ts`
- Create: `frontend/src/context/PreferencesContext.tsx`
- Modify: `frontend/src/pages/settings/useSettingsData.ts`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/index.tsx`
- Modify: `frontend/src/pages/settings/components/GeneralSettingsTab.tsx`

- [ ] **Step 1: 扩展设置类型**
  - 在设置接口中添加语音相关字段
  - 定义默认值
  - 明确这些字段属于全局偏好，供 Settings 和 Chat 共享

- [ ] **Step 2: 实现设置加载/保存**
  - 从现有 preferences API 读取语音设置
  - 保存时将语音字段与主题、语言、默认 Agent 一起写回
  - 保证缺省值在前端和后端都一致
  - 通过共享 Preferences Context 向 Chat 页提供同一份数据源

- [ ] **Step 3: 在设置页面添加 UI**
  - 添加"自动朗读"开关
  - 添加语速滑块
  - 添加语音选择下拉框（可选）

- [ ] **Step 4: 测试设置持久化**
  - 修改设置后刷新页面验证
  - 验证默认值正确
  - 在 Chat 页面验证同一份偏好状态被正确读取

- [ ] **Step 5: 提交**
```bash
git add frontend/src/context/PreferencesContext.tsx frontend/src/pages/settings/types.ts frontend/src/pages/settings/useSettingsData.ts frontend/src/pages/Settings.tsx frontend/src/index.tsx frontend/src/pages/settings/components/GeneralSettingsTab.tsx
git commit -m "feat: add speech synthesis settings"
```

---

### Task 3: Chat 页面自动触发

**Files:**
- Modify: `frontend/src/hooks/useChatState.ts`

- [ ] **Step 1: 导入语音 Hook**
  - 在 useChatState 中引入 useSpeechSynthesis
  - 初始化 Hook
  - 从共享 Preferences Context 读取自动朗读与语音参数

- [ ] **Step 2: 在流式响应结束时触发**
  - 仅在流式响应正常完成后触发，不在 abort / error / parse failure 场景触发
  - 读取用户设置
  - 调用 `speak()` 朗读最后一条 assistant 消息

- [ ] **Step 3: 实现跳过逻辑**
  - 检查消息是否为空
  - 检查是否为错误消息
  - 检查是否正在朗读

- [ ] **Step 4: 处理切换场景**
  - 用户开始新对话时停止当前朗读
  - 加载历史对话时停止当前朗读
  - 发送新请求前取消上一轮未完成的朗读，避免排队重叠

- [ ] **Step 5: 测试自动朗读**
  - 开启设置后发送消息
  - 验证朗读自动触发
  - 验证关闭设置后不触发

- [ ] **Step 6: 提交**
```bash
git add frontend/src/hooks/useChatState.ts
git commit -m "feat: auto-speak AI responses when enabled"
```

---

### Task 4: 手动控制组件

**Files:**
- Create: `frontend/src/components/SpeechControl.tsx`
- Modify: `frontend/src/components/MessageItem.tsx`

- [ ] **Step 1: 创建控制组件**
  - 设计按钮 UI（喇叭/暂停/播放图标）
  - 实现点击切换逻辑
  - 处理朗读状态显示

- [ ] **Step 2: 集成到消息组件**
  - 在 MessageItem 底部添加 SpeechControl
  - 仅对 assistant 消息显示
  - 传递消息内容
  - 按钮点击逻辑采用同一入口切换“开始朗读 / 停止当前朗读”

- [ ] **Step 3: 实现多消息管理**
  - 明确全局唯一的 speech controller 或 context，所有消息按钮共享同一实例
  - 同一时间只允许一个消息朗读
  - 点击新消息时停止当前朗读
  - 当前消息再次点击时直接停止该消息的朗读

- [ ] **Step 4: 测试手动控制**
  - 点击按钮验证朗读
  - 点击暂停验证暂停
  - 点击其他消息验证切换

- [ ] **Step 5: 提交**
```bash
git add frontend/src/components/SpeechControl.tsx frontend/src/components/MessageItem.tsx
git commit -m "feat: add manual speech control to messages"
```

---

### Task 5: 边界情况处理

**Files:**
- Modify: `frontend/src/hooks/useChatState.ts`
- Modify: `frontend/src/components/SpeechControl.tsx`

- [ ] **Step 1: 处理长文本**
  - 实现分段朗读（超过 200 字符截断）
  - 或限制单次朗读最大长度

- [ ] **Step 2: 处理 Markdown 格式**
  - 移除 Markdown 标记后再朗读
  - 或使用现有 markdown 工具函数清理

- [ ] **Step 3: 处理代码块**
  - 跳过代码块内容
  - 或简单提示"包含代码块"

- [ ] **Step 4: 处理多语言**
  - 根据内容自动选择语音
  - 或允许用户手动选择

- [ ] **Step 5: 错误处理**
  - 朗读失败时显示 Toast 提示
  - 记录错误日志
  - 自动朗读失败不阻断正常聊天流程
  - 手动按钮在“播放中”应切换为“停止”语义，而不是只负责暂停

- [ ] **Step 6: 提交**
```bash
git add frontend/src/hooks/useChatState.ts frontend/src/components/SpeechControl.tsx
git commit -m "fix: handle edge cases for speech synthesis"
```

---

### Task 6: 测试与优化

**Files:**
- Test: 手动测试 + 现有自动化测试

- [ ] **Step 1: 功能测试**
  - 自动朗读开启/关闭
  - 手动朗读控制
  - 设置持久化
  - 浏览器兼容性

- [ ] **Step 2: 边界测试**
  - 空消息
  - 错误消息
  - 超长消息
  - 快速切换对话

- [ ] **Step 3: 性能测试**
  - 朗读大段文本的响应时间
  - 内存泄漏检查

- [ ] **Step 4: 用户体验优化**
  - 调整默认语速
  - 优化按钮位置
  - 添加朗读中视觉反馈

- [ ] **Step 5: 运行现有测试套件**
```bash
cd frontend
npm test
```

- [ ] **Step 6: 提交最终优化**
```bash
git add frontend/src/
git commit -m "chore: polish speech synthesis feature"
```

---

## 测试策略

### 单元测试
- Hook 状态管理测试
- 设置加载/保存测试
- 边界条件测试

### 集成测试
- 自动朗读触发流程
- 手动控制交互流程
- 设置与功能联动

### 手动测试
- 多浏览器兼容性（Chrome/Safari/Firefox/Edge）
- 不同操作系统（macOS/Windows/Linux）
- 移动端浏览器（iOS Safari/Android Chrome）

---

## 验收标准

### 功能验收
- [ ] 设置页面有朗读开关且可保存
- [ ] 开启后 AI 回答完成自动朗读
- [ ] 关闭后不自动朗读
- [ ] 每条 AI 回复底部有手动朗读按钮
- [ ] 该按钮可对当前回复执行朗读或停止
- [ ] 可控制暂停/恢复/停止
- [ ] 长文本正确处理
- [ ] 错误消息不朗读

### 体验验收
- [ ] 朗读音质清晰
- [ ] 语速适中可调节
- [ ] 切换对话时朗读正确停止
- [ ] 无内存泄漏
- [ ] UI 响应流畅

### 兼容性验收
- [ ] Chrome/Edge 正常工作
- [ ] Safari 正常工作
- [ ] Firefox 正常工作（或优雅降级）
- [ ] 不支持的浏览器不报错

---

## 风险与缓解

### 风险 1: 浏览器兼容性
**问题:** 部分浏览器不支持 SpeechSynthesis API

**缓解:**
- 实现兼容性检测
- 不支持时隐藏相关 UI
- 显示友好提示
- 将不支持状态作为首类状态回传给 UI，而不是只在调用时报错

### 风险 2: 语音质量
**问题:** 不同浏览器/系统语音质量差异大

**缓解:**
- 提供语音选择功能
- 推荐高质量语音
- 允许用户自定义
- 默认优先系统默认语音，避免首次配置成本过高

### 风险 3: 长文本朗读
**问题:** 超长文本可能导致朗读中断或性能问题

**缓解:**
- 实现文本分段
- 限制单次朗读长度
- 提供进度指示
- 先在计划中确定文本清洗规则，再决定是否需要分段，避免后续实现时反复改动

---

## 未来扩展

### Phase 2: 高级功能
- 朗读历史记录
- 自定义语音包
- 后台朗读（切换到其他页面继续）
- 朗读播放列表

### Phase 3: AI 优化
- 智能断句优化朗读节奏
- 情感语调调整
- 多语言混合识别
- 专业术语发音优化

---

## 参考文档

- [Web Speech API MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [SpeechSynthesis MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis)
- 现有设置页面架构：`frontend/src/pages/settings/`
- 现有 Hook 模式：`frontend/src/hooks/`
