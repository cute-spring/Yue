# LLM Model Capability Inference Architecture

## 1. 业务背景 (Background)

在多模态（Vision）与深度推理（Reasoning）等新特性不断涌现的背景下，系统需要一种机制来准确判断**某个特定的 LLM 模型是否支持某项能力**。

过去，我们在各个业务模块（如 `chat.py` 或 `multimodal_service.py`）中散落着大量硬编码的名称匹配逻辑（例如判断名字里是否带 `vision` 或 `r1`）。这种方式导致了代码冗余、行为不一致（例如历史记录和实时聊天表现不同），且容易产生误判（例如将纯文本的 `gpt-4` 误认为支持视觉）。

为了解决这个问题，我们设计并落地了**集中式的 LLM 模型能力推断架构**。

---

## 2. 架构设计 (Architecture)

本架构遵循 **“配置优先 -> API 原生 -> 启发式推断”** 的三级降级策略，平衡了**确定性**与**灵活性（零配置冷启动）**。

### 2.1 判定优先级 (Resolution Priority)

当系统请求查询某模型（如 `openai/gpt-4o`）的能力时，按照以下顺序进行解析：

1. **静态配置优先 (Config First)**
   - 来源：`global_config.json` -> `llm.models.{provider/model}.capabilities`
   - 说明：如果管理员在配置文件中明确声明了该模型的能力数组（如 `["vision", "function_calling"]`），则直接使用该配置，忽略其他推断。这保证了最高级别的确定性。

2. **Provider 原生 API 级查询 (API Native)**
   - 来源：`Provider.get_model_capabilities(model_name)`
   - 说明：各 Provider 实现类（如 LiteLLM, OpenRouter, OpenAI）可以在拉取模型列表（`/models`）时，缓存 API 返回的原生元数据，并在此方法中返回。
   - 状态：已提供接口钩子，部分 Provider 正在逐步接入。

3. **启发式规则推断兜底 (Heuristic Fallback)**
   - 来源：`app.services.llm.capabilities.infer_capabilities`
   - 说明：如果前两者均未提供数据，系统将根据 `provider` 名称和 `model_name` 的字符串特征，结合正则与关键字列表（Tokens）自动推断。

---

## 3. 启发式推断规则详解 (Heuristics Detail)

集中在 `backend/app/services/llm/capabilities.py` 中维护。

### 3.1 视觉能力 (Vision)

**正向匹配 (Tokens)：**
包含 `"vision", "vl", "multimodal", "gpt-4o", "gpt-4.5", "claude-3", "gemini", "qwen-vl", "internvl", "llava", "cogvlm", "pixtral"`。

**排他策略 (Exclusions) - 防止误判：**
任何包含以下关键字的模型均被判定为**纯文本模型**，即使符合上面的正则：
- `"instruct", "text-only", "gpt-4-0613", "gpt-4-0314", "gpt-4-32k"`
- 特别处理：`provider == "openai"` 时，以 `gpt-4` 开头且不包含 `gpt-4-` 的模型（即原版 `gpt-4`），将被排除在视觉能力之外。

### 3.2 深度推理能力 (Reasoning)

**正向匹配 (Tokens)：**
包含 `"reasoner", "thought", "r1", "o1", "o3", "deepseek-v3"`。

### 3.3 函数调用能力 (Function Calling)

**正向匹配 (Tokens)：**
包含 `"gpt-4", "gpt-3.5", "claude-3", "gemini", "mistral-large", "mixtral-8x7b", "deepseek-v3", "qwen-max", "llama-3"`。
- **Provider 兜底**：如果 `provider` 是 `openai`, `anthropic`, `google` 中的任何一个，默认赋予 `function_calling` 能力。

---

## 4. 核心代码结构 (Code Structure)

- **`backend/app/services/llm/capabilities.py`**
  - 核心逻辑引擎：`infer_capabilities(provider, model_name, explicit_caps)`
  - 单点测试用例：`backend/tests/test_capabilities_unit.py` (覆盖了大量模型组合与排他边缘 Case)。

- **`backend/app/services/llm/base.py`**
  - `SimpleProvider` 基类新增了 `get_model_capabilities(self, model_name)` 虚方法。

- **`backend/app/services/config_service.py`**
  - `get_model_capabilities()` 方法作为对外的唯一出口，封装了前文所述的“三级降级策略”。业务层（如 Chat API、多模态拦截器）只能通过该方法获取能力。

---

## 5. 扩展与维护指南 (How to Extend)

### 场景 A：新出了一个开源多模态模型，名字叫 `super-vision-1.0`
**操作**：无需任何代码改动。只要名称中包含 `vision`，启发式引擎会自动识别。

### 场景 B：新出了一个闭源多模态模型，名字叫 `matrix-x`（不含任何 vision 特征）
**操作 1（推荐给管理员）**：在 `global_config.json` 中，为该模型手动配置 `capabilities: ["vision", "function_calling"]`。
**操作 2（推荐给开发者）**：在 `capabilities.py` 的 `VISION_TOKENS` 列表中添加 `"matrix-x"` 关键字。

### 场景 C：接入了一个新的聚合 API（例如 OpenRouter）
**操作**：在对应的 Provider 实现类中（如 `OpenRouterProvider`），重写 `get_model_capabilities` 方法。在拉取模型列表时，将 API 返回的架构数据（如 `architecture.modality`）解析并转换为内部标准的 capability 数组并返回。这比正则匹配更精确。
