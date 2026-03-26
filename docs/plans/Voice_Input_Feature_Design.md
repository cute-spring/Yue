# 语音输入功能设计方案

## 一、需求概述

### 1.1 功能目标
在聊天界面添加语音输入按钮，支持用户通过语音快速输入消息，提升输入效率和无障碍体验。

### 1.2 核心需求
- **双方案支持**：支持 Browser Speech API 与 Azure Speech Service
- **安全优先**：Azure Speech 密钥仅保存在后端，通过短期 Token 下发前端
- **后台可配置**：用户可在设置页设置默认 Provider，Agent 可按需覆盖
- **无缝集成**：与现有聊天输入框深度集成，不破坏现有交互流程
- **自动降级**：Azure 不可用时自动回退到 Browser Speech

### 1.3 用户场景
1. **快速输入场景**：用户希望快速口述长文本消息
2. **移动场景**：不方便打字时（走路、开车等）
3. **无障碍场景**：手部不便或视觉障碍用户
4. **多语言场景**：支持中文、英文等多语言识别

---

## 二、技术方案设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   前端 (Frontend)                    │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐   │
│  │          ChatInput 组件增强                    │   │
│  │  ┌────────────┐  ┌──────────────────────┐    │   │
│  │  │ 语音按钮    │  │  语音输入控制器        │    │   │
│  │  │ (Mic Icon) │  │  - 录音状态管理        │    │   │
│  │  └────────────┘  │  - 识别结果监听        │    │   │
│  │                  │  - 方案切换逻辑        │    │   │
│  │                  └──────────────────────┘    │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         语音方案抽象层 (Strategy Pattern)     │   │
│  │  ┌──────────────┐  ┌──────────────────┐     │   │
│  │  │ WebSpeech    │  │ ThirdPartySDK    │     │   │
│  │  │ Provider     │  │ Provider         │     │   │
│  │  └──────────────┘  └──────────────────┘     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                         │
                         │ (Azure 需要后端 Token Broker)
                         ▼
┌─────────────────────────────────────────────────────┐
│                   后端 (Backend)                     │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐   │
│  │         AgentConfig 配置模型增强               │   │
│  │  - voice_input_enabled: boolean              │   │
│  │  - voice_input_provider: 'browser'|'azure'   │   │
│  │  - voice_azure_config: JSON (后端存密钥)      │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         Preferences 配置模型增强               │   │
│  │  - voice_input_provider: 'browser'|'azure'   │   │
│  │  - voice_input_language: string              │   │
│  │  - voice_input_show_interim: boolean         │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         Speech Token Broker                   │   │
│  │  - /api/speech/stt/token                     │   │
│  │  - 返回 Azure 短期 Token                      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 2.2 前端设计

#### 2.2.1 语音输入控制器 (VoiceInputController)

**职责**：
- 统一管理语音识别生命周期
- 抽象不同语音方案的差异
- 提供一致的识别结果回调接口

**核心方法**：
```typescript
interface VoiceInputController {
  // 初始化
  initialize(config: VoiceInputConfig): void;
  
  // 开始录音
  startRecording(): Promise<void>;
  
  // 停止录音
  stopRecording(): void;
  
  // 取消录音
  cancelRecording(): void;
  
  // 是否正在录音
  isRecording(): boolean;
  
  // 是否支持语音输入
  isSupported(): boolean;
  
  // 获取当前方案
  getCurrentProvider(): 'web' | 'sdk' | null;
}
```

**状态管理**：
```typescript
interface VoiceInputState {
  isRecording: boolean;      // 是否正在录音
  isProcessing: boolean;     // 是否正在识别
  transcript: string;        // 当前识别结果
  interimTranscript: string; // 临时识别结果（流式）
  error: string | null;      // 错误信息
  provider: 'web' | 'sdk';   // 当前使用的方案
}
```

#### 2.2.2 语音方案提供者

**方案 A：Web Speech API Provider**

**实现要点**：
- 使用 `SpeechRecognition` 或 `webkitSpeechRecognition`
- 支持连续识别和实时结果（`interimResults`）
- 自动处理浏览器兼容性
- 支持语言切换（`lang` 属性）

**优势**：
- 零成本，无需后端
- 浏览器原生支持，延迟低
- 隐私友好（本地识别）

**劣势**：
- Safari/Firefox 支持有限
- 识别准确率依赖浏览器引擎
- 无法自定义识别模型

**方案 B：Azure Speech Provider**

**实现要点**：
- 集成 Azure Speech SDK
- 通过后端 `/api/speech/stt/token` 获取短期 Token
- 支持自定义 Endpoint ID
- API Key 仅保存在后端

**优势**：
- 云端识别质量稳定
- 鉴权方式适合企业部署
- 支持自定义 Speech Endpoint
- 可与 Browser Speech 形成主备架构

**劣势**：
- 需要网络请求，有延迟
- 有服务成本
- 隐私考虑（音频上传云端）

#### 2.2.3 ChatInput 组件集成

**UI 布局**：
```
┌─────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────┐    │
│  │  [LLM] [🧠] [📎] [🎤]                       │    │
│  │   模型  深度  图片  语音                      │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  请输入消息...                               │    │
│  │                                              │    │
│  │  [识别中的文字实时显示...]                   │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  [设置]                              [发送]   │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**交互逻辑**：
1. **点击语音按钮**：
   - 检查浏览器权限
   - 开始录音，按钮变为红色脉动状态
   - 显示"正在听..."提示

2. **识别过程中**：
   - 实时显示识别结果（灰色文字）
   - 支持手动点击停止
   - 支持继续说话（连续识别）

3. **识别完成**：
   - 自动填充到输入框
   - 光标定位到末尾
   - 可按 Enter 发送或继续编辑

4. **错误处理**：
   - 权限被拒绝：显示引导提示
   - 网络错误：自动降级到 Web API 或提示重试
   - 识别失败：显示友好错误信息

### 2.3 后端设计

#### 2.3.1 AgentConfig 模型增强

**新增字段**：
```python
class AgentConfig(BaseModel):
    # ... 现有字段 ...
    
    # 语音输入配置
    voice_input_enabled: bool = True
    voice_input_provider: str = "browser"       # 'browser' | 'azure'
    voice_azure_config: Optional[dict] = None   # region/api_key/endpoint_id，仅后端保存密钥
```

**配置说明**：
- `voice_input_enabled`：Agent 级别开关
- `voice_input_provider`：Agent 级别 Provider 覆盖
- `voice_azure_config`：后端安全存储，不回传 API Key

#### 2.3.2 Preferences 模型增强

**新增字段**：
```typescript
interface Preferences {
    // ... 现有字段 ...
    
    // 语音输入偏好
    voice_input_provider: 'browser' | 'azure'; // 全局默认 Provider
    voice_input_language: string;       // 默认语言
    voice_input_show_interim: boolean;  // 显示临时识别结果
}
```

#### 2.3.3 配置 API 变更

**GET /api/config/preferences**：
- 返回语音输入偏好

**POST /api/config/preferences**：
- 支持保存语音输入偏好

**GET /api/agents**：
- 返回每个 Agent 的语音输入配置，Azure 密钥必须脱敏

**POST /api/agents**：
- 支持保存 Agent 的语音输入配置

**GET /api/speech/stt/token**：
- 为 Azure Speech 返回短期 Token

---

## 三、配置管理设计

### 3.1 配置层级

```
用户偏好 (Preferences)
    ├── voice_input_provider: 'browser' | 'azure'
    ├── voice_input_language: 'zh-CN'
    └── voice_input_show_interim: true/false

Agent 配置 (AgentConfig)
    ├── voice_input_enabled: true/false
    ├── voice_input_provider: 'browser'|'azure'
    └── voice_azure_config: { region, endpoint_id, api_key(server-only) }
```

### 3.2 配置优先级

```
Agent 配置 > 用户偏好 > 系统默认
```

**说明**：
1. Agent 配置优先决定是否启用以及是否指定 Azure Speech
2. Agent 未指定云端 Provider 时，回退到用户偏好中的默认 Provider
3. Azure Token 获取失败、SDK 加载失败或浏览器不支持时，自动降级到 Browser Speech
4. Browser Speech 也不可用时，禁用麦克风按钮

### 3.3 配置 UI 位置

**设置页面**：
- **General Settings** → **Voice Input** 分组
  - 默认方案选择（Browser / Azure）
  - 默认语言选择
  - 显示临时识别结果开关

**Agents 管理页面**：
- **编辑 Agent** → **Voice Input** 分组
  - 启用/禁用语音输入
  - 选择语音方案
  - 配置 SDK（如选择第三方）
  - 支持的语言多选

---

## 四、第三方 SDK 集成方案

### 4.1 推荐 SDK

**Azure Speech Services**

| 特性 | 说明 |
|------|------|
| 准确率 | ⭐⭐⭐⭐⭐ |
| 免费额度 | 5 小时/月 |
| 延迟 | 低 |
| 方言支持 | 部分支持 |
| 推荐度 | ⭐⭐⭐⭐ |

**Google Cloud Speech-to-Text**

| 特性 | 说明 |
|------|------|
| 准确率 | ⭐⭐⭐⭐⭐ |
| 免费额度 | 60 分钟/月 |
| 延迟 | 低 |
| 方言支持 | 支持 |
| 推荐度 | ⭐⭐⭐ |

### 4.2 Azure Speech 集成方案

**配置项**：
```typescript
interface AzureSpeechConfig {
    apiKey: string;      // Azure Cognitive Services API Key
    region: string;      // Azure 区域 (如 eastasia, westus)
}
```

**集成方式**：
1. 用户在 Agents 管理页面配置 API Key 和区域
2. 前端使用 Azure Speech SDK 建立连接
3. 实时上传音频流，接收识别结果
4. 支持自定义发音词典和语言模型

**安全考虑**：
- 密钥存储在后端加密（可选）
- 前端通过后端代理获取临时 Token
- 避免密钥硬编码在前端代码

---

## 五、浏览器兼容性

### 5.1 Web Speech API 支持情况

| 浏览器 | 版本要求 | 支持程度 | 备注 |
|--------|----------|----------|------|
| Chrome | 25+ | ✅ 完全支持 | 推荐使用 |
| Edge | 79+ | ✅ 完全支持 | Chromium 内核 |
| Safari | 14.1+ | ⚠️ 部分支持 | 需要用户授权 |
| Firefox | 无 | ❌ 不支持 | 需降级到第三方 |
| Opera | 27+ | ✅ 完全支持 | Chromium 内核 |

### 5.2 降级策略

```
1. 检测浏览器是否支持 SpeechRecognition
   ├─ 支持 → 使用 Web Speech API
   └─ 不支持
      ├─ 配置了第三方 SDK → 使用第三方 SDK
      └─ 未配置 → 隐藏语音按钮，显示不可用提示
```

---

## 六、性能优化

### 6.1 延迟优化

**Web Speech API**：
- 首字延迟：< 200ms（本地识别）
- 实时性：流式输出，逐词显示

**第三方 SDK**：
- 首字延迟：500-800ms（网络 + 识别）
- 实时性：分片上传，逐句返回

**优化措施**：
1. 预加载 SDK（用户打开聊天页时初始化）
2. 音频分片上传（每 100ms 一片）
3. 识别结果缓存（避免重复识别）

### 6.2 资源优化

**内存管理**：
- 录音结束后立即释放 AudioContext
- 清理未使用的语音识别实例
- 避免内存泄漏（useEffect cleanup）

**网络优化**：
- 第三方 SDK 使用 WebSocket（长连接）
- 音频压缩（16kbps Opus 编码）
- 失败重试机制（指数退避）

---

## 七、安全与隐私

### 7.1 权限管理

**麦克风权限**：
- 首次使用时请求权限
- 权限被拒绝时显示引导
- 支持在浏览器设置中重新授权

**权限状态检测**：
```typescript
async function checkMicPermission(): Promise<'granted' | 'denied' | 'prompt'> {
  if (!navigator.permissions) return 'prompt';
  const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
  return result.state;
}
```

### 7.2 数据隐私

**Web Speech API**：
- ✅ 音频数据本地处理
- ✅ 不上传云端
- ✅ 无隐私风险

**第三方 SDK**：
- ⚠️ 音频上传到服务商服务器
- ⚠️ 需阅读隐私政策
- ✅ 建议选择合规服务商（GDPR/CCPA）

### 7.3 配置安全

**密钥管理**：
- 第三方 SDK 密钥存储在后端
- 前端通过代理获取临时 Token
- 支持密钥轮换

---

## 八、测试策略

### 8.1 单元测试

**测试覆盖**：
- VoiceInputController 状态管理
- Web Speech API 封装逻辑
- 第三方 SDK 封装逻辑
- 配置加载和保存

### 8.2 集成测试

**测试场景**：
1. 点击语音按钮 → 开始录音 → 识别成功 → 填充输入框
2. 权限被拒绝 → 显示错误提示
3. 切换语音方案 → 配置生效
4. 多语言识别 → 正确识别中英文

### 8.3 端到端测试

**测试用例**：
1. Chrome 浏览器完整流程
2. Safari 浏览器兼容性
3. 网络中断降级
4. 长文本识别（> 1 分钟）

---

## 九、验收标准

### 9.1 功能验收

- [ ] 聊天输入框显示语音按钮
- [ ] 点击按钮可开始/停止录音
- [ ] 识别结果正确填充到输入框
- [ ] 支持中文和英文识别
- [ ] 支持临时识别结果实时显示
- [ ] 权限被拒绝时显示友好提示

### 9.2 配置验收

- [ ] 设置页面可切换语音方案
- [ ] Agents 管理页可配置语音输入
- [ ] 配置保存后重新加载生效
- [ ] 不支持的浏览器隐藏语音按钮

### 9.3 体验验收

- [ ] 录音状态有明显视觉反馈（脉动动画）
- [ ] 识别结果逐字/逐句显示流畅
- [ ] 识别完成自动填充无延迟
- [ ] 错误提示清晰易懂

---

## 十、未来扩展

### 10.1 短期扩展

1. **语音命令支持**：
   - "发送消息"语音命令
   - "清空输入"语音命令
   - "换行"语音命令

2. **多语言混合识别**：
   - 中英文混合识别
   - 自动语言检测

3. **语音编辑功能**：
   - "删除上一句"
   - "撤销"语音命令

### 10.2 长期扩展

1. **离线识别**：
   - 集成 Vosk 等离线引擎
   - 无网络环境可用

2. **声纹识别**：
   - 多用户语音区分
   - 个性化识别模型

3. **实时翻译**：
   - 语音输入 → 自动翻译 → 发送外语

---

## 十一、技术债务规避

### 11.1 架构设计原则

1. **策略模式**：语音方案可插拔，易于扩展新 SDK
2. **单一职责**：控制器只管理状态，UI 组件只负责渲染
3. **依赖注入**：配置通过 Props 传递，便于测试
4. **错误边界**：语音识别失败不影响聊天功能

### 11.2 代码规范

1. **TypeScript 严格模式**：类型安全，避免运行时错误
2. **React Hooks 规范**：正确的依赖数组和 cleanup
3. **错误处理**：统一的错误上报和日志
4. **文档注释**：关键函数和接口添加 JSDoc

### 11.3 性能监控

1. **识别延迟监控**：记录从开始录音到首字显示的时间
2. **成功率监控**：记录识别失败次数和原因
3. **用户行为分析**：统计语音使用频率和场景

---

## 十二、总结

### 12.1 核心优势

1. **双方案保障**：Web API 免费便捷，第三方 SDK 高准确率
2. **配置灵活**：用户和 Agent 两级配置，满足不同场景
3. **体验优先**：实时识别、状态反馈、错误降级
4. **易于扩展**：策略模式支持未来新增 SDK

### 12.2 实施建议

1. **分阶段实施**：
   - Phase 1：Web Speech API 基础功能
   - Phase 2：配置管理和 UI 集成
   - Phase 3：第三方 SDK 集成
   - Phase 4：测试和优化

2. **风险控制**：
   - 优先保证 Web API 方案稳定
   - 第三方 SDK 作为可选增强
   - 充分的浏览器兼容性测试

3. **用户反馈**：
   - 上线后收集使用数据
   - 根据反馈调整默认配置
   - 持续优化识别体验
