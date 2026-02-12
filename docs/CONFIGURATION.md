# Yue 系统配置指南

本文档详细介绍了 `backend/data/global_config.json` 中各项配置参数的作用、取值建议以及安全实践。

## 1. 核心设计原则

- **优先级策略**: `global_config.json` > 环境变量 (`.env`)。
- **动态加载**: 大部分配置支持动态加载，无需重启后端服务（通过 `/api/models/providers` 刷新）。
- **敏感信息屏蔽**: API 返回配置信息时会自动脱敏敏感字段（如 API Key）。

---

## 2. LLM 配置 (`llm`)

`llm` 对象包含了所有与大模型供应商相关的配置。

### 2.1 基础配置

| 参数名 | 作用 | 示例/取值 |
| :--- | :--- | :--- |
| `provider` | 系统默认使用的 LLM 供应商 | `zhipu`, `openai`, `ollama` |
| `enabled_providers` | UI 界面上启用的供应商列表 | `"openai,azure_openai,ollama"` |
| `llm_request_timeout` | 请求超时时间（秒） | `60` (建议内网环境适当调大) |
| `proxy_url` | 全局 HTTP 代理 | `http://127.0.0.1:7890` |
| `no_proxy` | 不走代理的域名/IP 列表 | `localhost, 127.0.0.1, .azure.com` |

### 2.2 模型列表控制 (`{provider}_enabled_models`)

系统通过以下两个参数对每个供应商的模型进行精细化过滤：

- **`{provider}_enabled_models`**: 字符串数组，存储模型 ID。
- **`{provider}_enabled_models_mode`**: 过滤模式。
    - `allowlist`: **白名单模式**。仅显示列表中的模型。
    - `denylist`: **黑名单模式**。隐藏列表中的模型，显示其他所有。
    - `off`: **禁用过滤**。显示该供应商发现的所有模型。

**配置示例 (Ollama):**
```json
{
  "ollama_enabled_models": ["deepseek-r1:1.5b", "qwen3:8b"],
  "ollama_enabled_models_mode": "allowlist"
}
```

### 2.3 Azure OpenAI 特有配置

| 参数名 | 作用 | 格式说明 |
| :--- | :--- | :--- |
| `azure_openai_endpoint` | 资源终点 URL | `https://your-resource.openai.azure.com` |
| `azure_openai_deployment` | 部署名映射（支持昵称） | `[昵称=]真实部署名[:API版本], ...` |
| `azure_openai_api_version`| 全局默认 API 版本 | `2024-06-01` |
| `azure_openai_token` | API 密钥认证 | 直接填写 API Key |
| `azure_tenant_id` | Entra ID 认证 (租户 ID) | 用于无 Key 模式下的身份验证 |

**昵称配置示例:**
`"gpt4o=enterprise-gpt-4o-prod:2024-06-01, o1=internal-o1-preview"`
*UI 将显示 `gpt4o`，但实际请求 Azure 的 `enterprise-gpt-4o-prod` 部署。*

---

## 3. 文档访问控制 (`doc_access`)

用于控制 Agent 扫描和读取本地文件的权限范围，是系统的安全防线。

- **`allow_roots`**: 允许读取的根路径列表。建议仅包含项目目录或特定的文档存放目录。
- **`deny_roots`**: 即使在 `allow_roots` 范围内，也明确禁止访问的路径（如 `.git`, `node_modules`, `venv` 等）。

**配置示例:**
```json
"doc_access": {
  "allow_roots": ["/Users/work/Yue", "/Users/work/docs"],
  "deny_roots": ["/Users/work/Yue/backend/venv"]
}
```

---

## 4. 最佳实践与建议

1. **环境变量注入**: 建议将 `openai_api_key` 等敏感信息留在 `.env` 文件中，而在 `global_config.json` 中保持为空或删除该键。系统会自动回退读取环境变量。
2. **内网证书配置**: 在企业代理环境下，若遇到 SSL 报错，请配置 `ssl_cert_file` 指向您的企业根证书 `.pem` 文件。
3. **超时管理**: 如果您使用的模型生成速度较慢（如高参数量本地模型），请将 `llm_request_timeout` 设置为 `120` 或更高。
4. **路径安全**: 始终确保 `allow_roots` 指向最小必要范围，防止路径穿越攻击。
