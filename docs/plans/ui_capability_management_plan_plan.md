# LLM Model Capability UI Management Plan

## 1. 背景与目标 (Background & Goals)

在完成了后端的 [LLM 模型能力推断架构 (LLM Capability Inference Architecture)](./LLM_Capability_Inference_Architecture.md) 之后，系统已经具备了“配置优先”的三级能力判定机制。

为了进一步降低使用门槛，提升系统的灵活性，我们计划将模型能力的配置能力暴露到前端 UI 界面（Settings 页面）。
**核心目标**：
1. 允许用户在前端直观地看到系统自动推断出的模型能力。
2. 允许用户通过 UI 强制覆盖（Override）模型的 `vision`、`reasoning` 等能力，以应对闭源特殊模型或推断失败的场景。
3. 保证对 Custom Models (自定义模型) 的无缝支持。

---

## 2. 交互设计 (UX / UI Design)

主要修改集中在 `frontend/src/pages/Settings.tsx` 中的两处组件：**Model Manager Modal** 和 **Add Custom Model Modal**。

### 2.1 Model Manager 弹窗升级 (Manage Models)

当前该弹窗仅用于勾选启用/禁用模型。升级后将增加能力覆盖功能。

**UI 表现：**
- 将原来的单列 Checkbox 列表改为网格/表格布局。
- 每行包含：
  - 模型名称 (Model Name)
  - 启用开关 (Enabled Toggle)
  - **能力标签组 (Capabilities Badges)**:
    - 提供 `[Vision]`, `[Reasoning]`, `[Function Calling]` 三个徽章。
    - **默认状态**：根据后端 API `/api/models/providers` 返回的 `model_capabilities` 渲染。如果是自动推断的，徽章显示为半透明/灰色边框；
    - **人工覆盖状态**：点击徽章即可 Toggle。一旦手动修改，徽章变为实色（如 Emerald 绿色），表示已被手动 Override。
- **重置功能**：提供一个小的“恢复默认”按钮，清除手动 Override，恢复为后端自动推断状态。

### 2.2 Add/Edit Custom Model 弹窗升级

自定义模型通常名称不规则，极度依赖手动配置能力。

**UI 表现：**
- 在填写 `Name`, `Provider`, `Base URL`, `API Key` 的表单下方，新增一个 "Model Capabilities" 区块。
- 提供三个明确的 Checkbox：
  - `[ ] Supports Vision (Image input)`
  - `[ ] Supports Deep Thinking (Reasoning)`
  - `[ ] Supports Function Calling (Tools)`
- 用户勾选后，随表单一起保存。

---

## 3. 前后端数据契约 (Data Contract)

### 3.1 前端状态管理 (`Settings.tsx`)

前端需要维护一个新的状态用于存储被 Override 的 capabilities：

```typescript
// Record<model_id, string[]>
const [capabilityOverrides, setCapabilityOverrides] = createSignal<Record<string, string[]>>({});
```

在点击 `Save All LLM Settings` 时，将该对象与原有的 `llmForm` 合并提交。

### 3.2 后端存储结构 (`global_config.json`)

目前后端的存储结构已经完美支持了该特性，无需进行结构上的破坏性修改。

```json
{
  "llm": {
    "models": {
      "openai/gpt-4o": {
        "enabled": true,
        "capabilities": ["vision", "function_calling"]
      },
      "openai/my-weird-model": {
        "enabled": true,
        "capabilities": ["reasoning"] 
      }
    },
    "custom_models": [
      {
        "name": "my-custom-vision",
        "provider": "openai",
        "model": "qwen-vl",
        "capabilities": ["vision"]
      }
    ]
  }
}
```

### 3.3 后端 API 适配 (`backend/app/services/config_service.py`)

在现有的 `update_llm_config` 方法中，确保当合并前端传来的 `models` 字典时，能够正确接收并持久化 `capabilities` 字段，且不会意外覆盖其他字段。

对于 Custom Models，修改 `upsert_custom_model` 方法，允许 `capabilities` 字段作为合法的 payload 属性被保存。

---

## 4. 实施步骤与排期 (Implementation Steps)

### Step 1: 后端数据写入支持 (0.5 天)
- [ ] 检查并完善 `config_service.py` 中的 `update_llm_config`，确保 `llm.models.{id}.capabilities` 能被正确更新和序列化。
- [ ] 确保 `/api/models/providers` 接口返回的结构中，清晰地区分了“显式配置的能力”和“推断出的能力”（可选：为前端提供一个 `explicit_capabilities` 字段以区分高亮状态）。

### Step 2: 前端组件重构 - Custom Models (0.5 天)
- [ ] 在 `Settings.tsx` 中找到 `showAddCustom` 弹窗。
- [ ] 添加能力复选框 UI。
- [ ] 在 `testCustomModel` 和 `upsertCustomModel` 逻辑中携带 `capabilities` 数组。

### Step 3: 前端组件重构 - Model Manager (1 天)
- [ ] 重构 `showModelManager` 弹窗的内部列表渲染逻辑。
- [ ] 引入交互式 Capability Badge 组件。
- [ ] 编写合并逻辑：保存时，仅将发生 override 的 capabilities 提取并合并进 `llmForm.models` 中提交。

### Step 4: 测试与验证 (0.5 天)
- [ ] **验证点 1**：在 UI 上给一个纯文本模型（如 `gpt-3.5-turbo`）强行勾选 Vision，保存后回到聊天界面，确认可以上传图片并触发多模态拦截逻辑。
- [ ] **验证点 2**：在 UI 上给一个非推理模型强行勾选 Reasoning，确认聊天界面的 Deep Thinking Toggle 可用。
- [ ] **验证点 3**：验证 Custom Models 添加时勾选能力，保存并重启服务后配置不丢失。

---

## 5. 潜在风险与缓解策略 (Risks & Mitigations)

1. **状态冲突风险**：如果后端自动推断逻辑升级了，导致原本不支持的能力变成了支持，而前端由于有历史 Override 导致无法同步更新。
   - **缓解策略**：前端必须明确区分“系统推断”与“人工配置”。提供一键清除 override 的功能，让配置回归后端托管。
2. **能力虚标导致运行时报错**：用户强行给不支持 Vision 的模型勾选了 Vision，发送图片后必定会在 API 层（如 OpenAI API）报错 `400 Bad Request`。
   - **缓解策略**：这是预期的行为（用户自己承担覆盖配置的后果）。但前端在捕获到大模型 API 的 400 错误时，需要有友好的 Toast 提示，建议用户检查 Settings 中的能力配置是否准确。
