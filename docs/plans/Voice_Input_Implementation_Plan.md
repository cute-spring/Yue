# 语音输入功能落实计划

**文档状态**：待执行  
**创建日期**：2026-03-24  
**预计工期**：5-7 天  
**优先级**：高  

---

## 一、计划概述

### 1.1 目标
在聊天界面实现语音输入功能，采用 `Azure Speech Service + Browser Speech 兜底` 架构。用户可在后台设置默认 Provider，Agent 可按需覆盖，Azure 密钥仅保存在后端并通过短期 Token 下发前端。

### 1.2 范围
- ✅ 前端语音输入组件开发
- ✅ Browser Speech Provider
- ✅ Azure Speech Provider
- ✅ 后端 Token Broker 与 Agent 配置脱敏
- ✅ 设置页面和 Agents 管理页配置 UI
- ✅ 聊天界面集成与自动降级
- ❌ 自建语音识别引擎

### 1.3 关键里程碑

```
Day 1-2:  后端配置模型 + 前端基础组件
Day 3:    设置页面配置 UI
Day 4:    Agents 管理页配置 UI
Day 5:    聊天界面集成 + 联调
Day 6-7:  测试 + 优化 + 文档
```

---

## 二、实施阶段

### Phase 1: 配置与安全模型（Day 1 上午）

#### 1.1 AgentConfig 模型扩展

**任务**：
- [ ] 在 `backend/app/services/agent_store.py` 中为 `AgentConfig` 添加字段：
  ```python
  voice_input_enabled: bool = True
  voice_input_provider: str = "browser"  # 'browser' | 'azure'
  voice_azure_config: Optional[dict] = None  # region/api_key/endpoint_id
  ```

- [ ] 更新内置 Agent 配置（如需要）：
  - `builtin-docs`：默认启用语音输入
  - `builtin-architect`：默认启用语音输入

**验收标准**：
- [ ] 新建 Agent 时语音字段有默认值
- [ ] 加载旧 Agent 配置时兼容缺失字段
- [ ] Azure 密钥仅后端保存
- [ ] 单元测试通过

**相关文件**：
- `backend/app/services/agent_store.py`
- `backend/tests/test_agent_store_unit.py`

**预计工时**：2 小时

---

#### 1.2 Preferences 配置扩展

**任务**：
- [ ] 查找 Preferences 定义位置（前端 types 或后端 config）
- [ ] 添加语音输入相关偏好字段：
  ```typescript
  voice_input_provider: 'browser' | 'azure';
  voice_input_language: string;
  voice_input_show_interim: boolean;
  ```

- [ ] 更新默认配置

**验收标准**：
- [ ] 设置页面可读取新配置项
- [ ] 配置可保存和加载

**相关文件**：
- `frontend/src/types/`（查找 Preferences 定义）
- `backend/app/services/config_service.py`

**预计工时**：1.5 小时

---

#### 1.3 配置 API 验证

**任务**：
- [ ] 验证 GET/POST `/api/config/preferences` 返回并保存新字段
- [ ] 验证 GET `/api/agents` 返回脱敏后的 Azure 配置
- [ ] 验证 POST/PUT `/api/agents` 可保存语音配置且不回显 API Key
- [ ] 验证 GET `/api/speech/stt/token` 可为 Azure Speech 返回短期 Token

**验收标准**：
- [ ] 使用 Postman 或测试脚本验证 API
- [ ] 配置保存后重新加载生效

**相关文件**：
- `backend/app/api/config.py`
- `backend/app/api/agents.py`

**预计工时**：1.5 小时

---

### Phase 2: 前端语音输入核心组件（Day 1 下午 - Day 2）

#### 2.1 语音输入控制器（VoiceInputController）

**任务**：
- [ ] 创建 `frontend/src/hooks/useVoiceInput.ts`
- [ ] 实现统一状态管理：
  ```typescript
  interface VoiceInputState {
    isRecording: boolean;
    isProcessing: boolean;
    transcript: string;
    interimTranscript: string;
    error: string | null;
    provider: 'web' | 'sdk';
  }
  ```

- [ ] 实现核心方法：
  - `initialize(config)`
  - `startRecording()`
  - `stopRecording()`
  - `cancelRecording()`
  - `isSupported()`

**验收标准**：
- [ ] 可正确管理录音状态
- [ ] 状态变更触发组件重绘
- [ ] 错误处理完善

**相关文件**：
- `frontend/src/hooks/useVoiceInput.ts`（新建）

**预计工时**：3 小时

---

#### 2.2 Web Speech API Provider

**任务**：
- [ ] 创建 `frontend/src/utils/VoiceProviders/WebSpeechProvider.ts`
- [ ] 封装浏览器 SpeechRecognition API：
  ```typescript
  class WebSpeechProvider implements IVoiceProvider {
    private recognition: SpeechRecognition | null;
    
    start(options: RecognitionOptions): void;
    stop(): void;
    cancel(): void;
    isSupported(): boolean;
  }
  ```

- [ ] 处理浏览器兼容性：
  - 检测 `window.SpeechRecognition` 或 `window.webkitSpeechRecognition`
  - 降级处理不支持的浏览器

- [ ] 支持特性：
  - 连续识别（`continuous = true`）
  - 实时结果（`interimResults = true`）
  - 语言切换（`lang` 属性）
  - 错误事件处理

**验收标准**：
- [ ] Chrome/Edge 下可正常录音和识别
- [ ] 识别结果逐字返回
- [ ] 错误事件正确捕获

**相关文件**：
- `frontend/src/utils/VoiceProviders/WebSpeechProvider.ts`（新建）
- `frontend/src/utils/VoiceProviders/types.ts`（新建接口定义）

**预计工时**：4 小时

---

#### 2.3 Azure Speech Provider

**任务**：
- [ ] 创建 `frontend/src/utils/VoiceProviders/AzureSpeechProvider.ts`
- [ ] 集成 Azure Speech SDK：
  - 引入 Azure Speech SDK（@microsoft/cognitiveservices-speech-sdk）
  - 封装 SpeechRecognizer 逻辑
  - 处理音频流上传

- [ ] 配置管理：
  - 从 AgentConfig 读取脱敏后的区域和 Endpoint 信息
  - 通过后端 `/api/speech/stt/token` 获取临时 Token
  - 前端不直接持有 API Key

- [ ] 实现接口：
  ```typescript
  class AzureSpeechProvider implements IVoiceProvider {
    private recognizer: SpeechRecognizer | null;
    private config: AzureSpeechConfig;
    
    start(options: RecognitionOptions): void;
    stop(): void;
    cancel(): void;
    isSupported(): boolean;
  }
  ```

**验收标准**：
- [ ] 配置正确后可连接 Azure 服务
- [ ] 识别结果正确返回
- [ ] 错误处理完善（网络错误、鉴权失败等）

**相关文件**：
- `frontend/src/utils/VoiceProviders/AzureSpeechProvider.ts`（新建）
- Azure Speech SDK 文档：https://learn.microsoft.com/azure/cognitive-services/speech-service/

**预计工时**：4 小时

---

#### 2.4 Provider 工厂和降级策略

**任务**：
- [ ] 创建 Provider 工厂：
  ```typescript
  function createVoiceProvider(config: VoiceInputConfig): IVoiceProvider {
    if (config.provider === 'sdk') {
      return new AzureSpeechProvider(config.sdkConfig);
    }
    return new WebSpeechProvider();
  }
  ```

- [ ] 在 `useVoiceInput` Hook 中集成工厂
- [ ] 支持运行时切换 Provider
- [ ] Azure 不可用时自动降级到 Browser Speech

**验收标准**：
- [ ] 根据配置自动选择 Provider
- [ ] 切换配置后重新初始化生效
- [ ] Azure Token/SDK 失败时可自动回退

**相关文件**：
- `frontend/src/utils/VoiceProviders/index.ts`（新建工厂）

**预计工时**：2 小时

---

### Phase 3: 设置页面配置 UI（Day 3 上午）

#### 3.1 GeneralSettingsTab 增强

**任务**：
- [ ] 在 `frontend/src/pages/settings/components/GeneralSettingsTab.tsx` 添加 Voice Input 分组
- [ ] 添加配置项：
  - 默认方案选择（下拉框：Browser / Azure）
  - 默认语言选择（下拉框：中文 / 英文 / 自动）
  - 显示临时识别结果（开关）
  - Azure 作为默认值时的回退说明

**UI 示例**：
```tsx
<div class="rounded-lg border border-gray-200 bg-gray-50/80 p-4 space-y-4">
  <h4 class="text-sm font-semibold text-gray-800">Voice Input</h4>
  
  <div>
    <label class="block text-sm font-medium text-gray-700 mb-1">
      Default Provider
    </label>
    <select name="voice_input_provider" class="w-full border rounded-lg p-2 bg-white">
      <option value="browser">Browser Speech API (Free)</option>
      <option value="azure">Azure Speech (Cloud)</option>
    </select>
  </div>
  
  <label class="flex items-center justify-between gap-3">
    <span class="text-sm font-medium text-gray-700">Show interim results</span>
    <input type="checkbox" name="voice_input_show_interim" class="h-4 w-4" />
  </label>
</div>
```

**验收标准**：
- [ ] 配置项显示正确
- [ ] 配置可保存和加载
- [ ] UI 风格与现有设置页一致

**相关文件**：
- `frontend/src/pages/settings/components/GeneralSettingsTab.tsx`

**预计工时**：2 小时

---

### Phase 4: Agents 管理页配置 UI（Day 3 下午）

#### 4.1 AgentForm 增强

**任务**：
- [ ] 在 `frontend/src/components/AgentForm.tsx` 添加 Voice Input 配置分组
- [ ] 添加配置项：
  - 启用语音输入（开关）
  - 语音方案选择（Browser / Azure）
  - Azure 配置输入（选择 Azure 时显示）
    - Region 输入框
    - Endpoint ID 输入框（可选）
    - API Key 输入框（仅提交到后端，不回显）

**UI 布局**：
```tsx
<div class="rounded-2xl border border-violet-100 bg-violet-50/60 p-4 space-y-4">
  <div class="flex items-center justify-between gap-3">
    <div>
      <div class="text-[10px] font-black text-violet-700 uppercase tracking-[0.2em]">
        Voice Input
      </div>
      <div class="text-xs text-violet-700/80 mt-1">
        Enable voice dictation for this agent
      </div>
    </div>
    <input type="checkbox" name="voice_input_enabled" class="h-4 w-4" />
  </div>
  
  <Show when={formVoiceInputEnabled()}>
    <!-- Provider selection, SDK config, languages -->
  </Show>
</div>
```

**验收标准**：
- [ ] 配置项显示正确
- [ ] Azure 配置条件渲染
- [ ] 配置可保存到 AgentConfig
- [ ] 已保存密钥在重新编辑时不回显，仅显示“已配置”

**相关文件**：
- `frontend/src/components/AgentForm.tsx`

**预计工时**：3 小时

---

#### 4.2 Agent 列表页显示

**任务**：
- [ ] 在 Agents 列表页添加语音输入状态标识
- [ ] 显示每个 Agent 是否启用语音输入
- [ ] 显示使用的语音方案图标

**UI 示例**：
```tsx
<div class="flex items-center gap-2">
  <Show when={agent.voice_input_enabled}>
    <span class="text-xs text-emerald-600" title="Voice input enabled">
      🎤
    </span>
  </Show>
  <Show when={agent.voice_input_provider === 'sdk'}>
    <span class="text-xs text-violet-600" title="Using third-party SDK">
      ⚡
    </span>
  </Show>
</div>
```

**验收标准**：
- [ ] 列表页可快速识别语音配置状态
- [ ] 图标含义清晰

**相关文件**：
- `frontend/src/pages/Agents.tsx`

**预计工时**：1 小时

---

### Phase 5: 聊天界面集成（Day 4）

#### 5.1 ChatInput 组件增强

**任务**：
- [ ] 在 `frontend/src/components/ChatInput.tsx` 添加语音按钮
- [ ] 语音按钮位置：在图片上传按钮旁边
- [ ] 按钮状态：
  - 默认：麦克风图标（灰色）
  - 录音中：红色脉动动画
  - 识别中：蓝色呼吸灯效果
  - 不可用：禁用状态（灰色）

**UI 实现**：
```tsx
<Show when={voiceInputEnabled}>
  <div class="relative group/tooltip">
    <button
      type="button"
      onClick={handleVoiceButtonClick}
      class={`p-2.5 rounded-2xl transition-all ${
        isRecording
          ? 'bg-red-500 text-white animate-pulse'
          : 'text-slate-500 hover:text-primary hover:bg-primary/10'
      }`}
      aria-label="Voice input"
    >
      <svg><!-- 麦克风图标 --></svg>
    </button>
    
    {/* 录音状态提示 */}
    <Show when={isRecording}>
      <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 px-3 py-1.5 bg-red-500 text-white text-xs rounded-lg whitespace-nowrap">
        Listening...
      </div>
    </Show>
  </div>
</Show>
```

**验收标准**：
- [ ] 按钮显示在正确位置
- [ ] 状态动画流畅
- [ ] 点击可开始/停止录音

**相关文件**：
- `frontend/src/components/ChatInput.tsx`

**预计工时**：3 小时

---

#### 5.2 识别结果填充逻辑

**任务**：
- [ ] 监听语音识别结果事件
- [ ] 识别结果填充到输入框：
  ```typescript
  useEffect(() => {
    const handleTranscript = (e: CustomEvent<string>) => {
      setInput(e.detail); // 填充到输入框
    };
    
    window.addEventListener('voice:transcript', handleTranscript);
    return () => window.removeEventListener('voice:transcript', handleTranscript);
  }, []);
  ```

- [ ] 支持临时识别结果（灰色显示）
- [ ] 识别完成后自动定位光标

**验收标准**：
- [ ] 识别结果实时填充
- [ ] 临时结果和最终结果区分显示
- [ ] 光标位置正确

**相关文件**：
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/pages/Chat.tsx`

**预计工时**：2 小时

---

#### 5.3 Chat 页面集成

**任务**：
- [ ] 在 `frontend/src/pages/Chat.tsx` 中初始化语音输入控制器
- [ ] 从 AgentConfig 读取语音配置
- [ ] 根据配置选择 Provider
- [ ] 处理 Agent 切换时的配置更新
- [ ] Azure 失败时自动回退到 Browser Speech

**集成逻辑**：
```typescript
const voiceConfig = createMemo(() => {
  const agent = agents().find(a => a.name === activeAgentName());
  return {
    enabled: agent?.voice_input_enabled ?? true,
    provider: agent?.voice_input_provider ?? prefs.voice_input_provider ?? 'browser',
    azureConfigured: agent?.voice_azure_config?.api_key_configured ?? false,
  };
});

const voiceInput = useVoiceInput(voiceConfig);
```

**验收标准**：
- [ ] 不同 Agent 使用不同语音配置
- [ ] 切换 Agent 时语音配置同步更新
- [ ] 配置未启用时隐藏语音按钮
- [ ] Azure 不可用时自动退回 Browser Speech

**相关文件**：
- `frontend/src/pages/Chat.tsx`

**预计工时**：2 小时

---

### Phase 6: 错误处理和降级（Day 5 上午）

#### 6.1 权限处理

**任务**：
- [ ] 检测麦克风权限
- [ ] 权限被拒绝时显示引导：
  ```tsx
  <Show when={permissionState === 'denied'}>
    <div class="p-4 rounded-lg bg-amber-50 border border-amber-200">
      <div class="font-semibold text-amber-800">麦克风权限被拒绝</div>
      <div class="text-sm text-amber-700 mt-1">
        请在浏览器设置中允许麦克风权限，然后重试。
      </div>
      <button onClick={requestPermission} class="mt-2 px-4 py-2 bg-amber-500 text-white rounded-lg">
        重新请求权限
      </button>
    </div>
  </Show>
  ```

**验收标准**：
- [ ] 权限检测准确
- [ ] 引导提示清晰

**预计工时**：1.5 小时

---

#### 6.2 浏览器兼容性降级

**任务**：
- [ ] 检测浏览器是否支持 Web Speech API
- [ ] 不支持时自动降级到第三方 SDK
- [ ] 两者都不支持时隐藏语音按钮

**降级逻辑**：
```typescript
function checkSupport(): 'web' | 'sdk' | null {
  if (window.SpeechRecognition || window.webkitSpeechRecognition) {
    return 'web';
  }
  if (config.provider === 'sdk' && config.sdkConfig) {
    return 'sdk';
  }
  return null;
}
```

**验收标准**：
- [ ] 降级逻辑正确
- [ ] 不支持的浏览器不显示按钮

**预计工时**：1 小时

---

#### 6.3 错误边界

**任务**：
- [ ] 语音识别失败不影响聊天功能
- [ ] 错误日志记录
- [ ] 用户友好的错误提示

**错误类型**：
- 网络错误（第三方 SDK）
- 识别超时
- 音频设备错误
- 服务不可用

**验收标准**：
- [ ] 所有错误有对应提示
- [ ] 错误可恢复

**预计工时**：1.5 小时

---

### Phase 7: 测试和优化（Day 5 下午 - Day 6）

#### 7.1 单元测试

**任务**：
- [ ] 为 `useVoiceInput` Hook 编写测试
- [ ] 为 Provider 工厂编写测试
- [ ] 为 WebSpeechProvider 编写测试（Mock）
- [ ] 为配置加载编写测试

**测试文件**：
- `frontend/src/hooks/useVoiceInput.test.ts`
- `frontend/src/utils/VoiceProviders/WebSpeechProvider.test.ts`

**验收标准**：
- [ ] 核心逻辑测试覆盖率 > 80%
- [ ] 所有测试通过

**预计工时**：3 小时

---

#### 7.2 集成测试

**任务**：
- [ ] 编写 Playwright 端到端测试
- [ ] 测试场景：
  1. 点击语音按钮 → 录音 → 识别成功 → 发送消息
  2. 权限被拒绝 → 显示引导
  3. 切换 Agent → 语音配置更新
  4. 切换语音方案 → 配置生效

**测试文件**：
- `frontend/tests/voice-input.spec.ts`

**验收标准**：
- [ ] 所有集成测试通过
- [ ] 关键路径无 Bug

**预计工时**：3 小时

---

#### 7.3 性能优化

**任务**：
- [ ] 优化首字延迟（目标 < 300ms）
- [ ] 优化内存使用（录音结束后释放资源）
- [ ] 优化识别流畅度（减少卡顿）

**优化措施**：
1. 预加载 SDK（页面初始化时）
2. 音频分片处理（避免阻塞）
3. 状态更新节流（减少重绘）

**验收标准**：
- [ ] 性能指标达标
- [ ] 无明显卡顿

**预计工时**：2 小时

---

#### 7.4 用户体验优化

**任务**：
- [ ] 优化录音状态动画（流畅脉动）
- [ ] 优化识别结果显示（逐字高亮）
- [ ] 优化错误提示（清晰易懂）
- [ ] 添加快捷键支持（如 Ctrl+M 开关语音）

**验收标准**：
- [ ] 用户体验流畅
- [ ] 视觉反馈清晰

**预计工时**：2 小时

---

### Phase 8: 文档和培训（Day 7）

#### 8.1 用户文档

**任务**：
- [ ] 更新用户手册：
  - 如何使用语音输入
  - 如何配置语音方案
  - 常见问题解答

**文档位置**：
- `docs/user-guide/voice-input.md`

**验收标准**：
- [ ] 文档清晰易懂
- [ ] 包含截图和示例

**预计工时**：2 小时

---

#### 8.2 开发者文档

**任务**：
- [ ] 更新 API 文档：
  - AgentConfig 新增字段说明
  - Preferences 新增字段说明

- [ ] 更新架构文档：
  - 语音输入架构图
  - Provider 接口说明

**文档位置**：
- `docs/api/voice-input.md`
- `docs/architecture/voice-input-design.md`

**验收标准**：
- [ ] 文档完整
- [ ] 代码注释完善

**预计工时**：2 小时

---

#### 8.3 团队培训

**任务**：
- [ ] 组织功能演示会
- [ ] 分享技术实现细节
- [ ] 收集反馈意见

**验收标准**：
- [ ] 团队成员了解功能
- [ ] 反馈问题记录在案

**预计工时**：1 小时

---

## 三、风险管理

### 3.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Web Speech API 浏览器兼容性差 | 中 | 高 | 准备第三方 SDK 降级方案 |
| 第三方 SDK 识别延迟高 | 中 | 中 | 优化网络请求，使用 WebSocket |
| 麦克风权限被系统限制 | 低 | 高 | 提供明确的权限引导 |
| 长文本识别准确率低 | 中 | 中 | 分段识别，支持手动修正 |

### 3.2 进度风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 第三方 SDK 集成复杂度高 | 中 | 中 | 优先完成 Web API，SDK 作为可选 |
| 测试用例覆盖不足 | 高 | 中 | 提前编写测试计划，预留缓冲时间 |
| UI/UX 反复修改 | 中 | 低 | 提前确认设计方案，减少返工 |

---

## 四、验收清单

### 4.1 功能验收

- [ ] 聊天输入框显示语音按钮
- [ ] 点击按钮可开始/停止录音
- [ ] 识别结果正确填充到输入框
- [ ] 支持中文和英文识别
- [ ] 支持临时识别结果实时显示
- [ ] 权限被拒绝时显示友好提示
- [ ] 不支持的浏览器隐藏语音按钮

### 4.2 配置验收

- [ ] 设置页面可切换语音方案
- [ ] Agents 管理页可配置语音输入
- [ ] 配置保存后重新加载生效
- [ ] 不同 Agent 使用不同语音配置
- [ ] SDK 配置条件渲染正确

### 4.3 体验验收

- [ ] 录音状态有明显视觉反馈
- [ ] 识别结果逐字/逐句显示流畅
- [ ] 识别完成自动填充无延迟
- [ ] 错误提示清晰易懂
- [ ] 快捷键支持（如 Ctrl+M）

### 4.4 测试验收

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试全部通过
- [ ] 端到端测试覆盖关键路径
- [ ] 性能指标达标（首字延迟 < 300ms）

### 4.5 文档验收

- [ ] 用户手册更新
- [ ] API 文档更新
- [ ] 架构文档更新
- [ ] 代码注释完善

---

## 五、后续优化方向

### 5.1 短期优化（1-2 周）

1. **语音命令支持**：
   - "发送"、"清空"、"换行"等命令
   - 命令词自定义

2. **多语言混合识别**：
   - 中英文自动切换
   - 方言支持（粤语、四川话）

3. **识别历史**：
   - 保存最近 10 条语音识别记录
   - 支持快速重新插入

### 5.2 中期优化（1-2 月）

1. **离线识别**：
   - 集成 Vosk 等离线引擎
   - 无网络环境可用

2. **个性化模型**：
   - 学习用户语音特征
   - 提升个人识别准确率

3. **实时翻译**：
   - 语音输入 → 自动翻译 → 发送外语

### 5.3 长期优化（3-6 月）

1. **声纹识别**：
   - 多用户语音区分
   - 个性化配置自动切换

2. **语音助手**：
   - 语音控制界面操作
   - 语音导航

3. **会议模式**：
   - 多人语音识别
   - 说话人分离

---

## 六、资源需求

### 6.1 人力资源

- **前端开发**：1 人 × 5 天
- **后端开发**：0.5 人 × 2 天
- **测试**：0.5 人 × 2 天
- **UI/UX 设计**：0.5 人 × 1 天

### 6.2 第三方资源

- **讯飞 SDK**：免费额度 500 次/天（开发测试足够）
- **浏览器**：Chrome/Edge/Safari 最新版

### 6.3 设备需求

- 麦克风设备（笔记本内置或外置）
- 多浏览器测试环境

---

## 七、总结

### 7.1 关键成功因素

1. **分阶段实施**：先 Web API 后第三方，降低风险
2. **配置灵活**：用户和 Agent 两级配置，满足不同场景
3. **体验优先**：实时识别、状态反馈、错误降级
4. **测试充分**：单元测试 + 集成测试 + 端到端测试

### 7.2 预期收益

1. **用户体验提升**：语音输入效率提升 3-5 倍（长文本场景）
2. **无障碍支持**：为视觉障碍用户提供便利
3. **竞争力增强**：差异化功能，提升产品吸引力
4. **技术积累**：为未来语音交互功能打下基础

### 7.3 下一步行动

1. [ ] 确认计划和时间表
2. [ ] 分配开发资源
3. [ ] 准备开发环境
4. [ ] 开始 Phase 1 实施

---

**审批**：
- [ ] 产品经理审批
- [ ] 技术负责人审批
- [ ] 项目负责人审批

**更新日期**：2026-03-24
