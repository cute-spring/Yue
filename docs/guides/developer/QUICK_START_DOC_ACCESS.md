# 文档访问快速配置指南

**5 分钟配置完成，让 Agent 可以访问项目内外的文档**

---

## 🎯 配置目标

- ✅ **默认池**：当前项目根目录（`.`）下的所有文档
- ✅ **扩展池**：1 个或多个项目外的绝对路径目录

---

## 📋 方案一：配置文件（推荐）⭐

### 步骤 1：创建配置文件

在项目根目录执行：

```bash
# 复制示例配置文件
cp backend/data/global_config.json.example backend/data/global_config.json

# 编辑配置文件
vim backend/data/global_config.json
```

### 步骤 2：修改配置

找到 `doc_access` 部分，修改为：

```json
{
  "doc_access": {
    "allow_roots": [
      ".",
      "/Users/your-name/other-project/docs",
      "/opt/company-docs"
    ],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv"
    ]
  }
}
```

**配置说明**：
- `"."` → **默认池**：当前项目根目录
- `"/Users/your-name/other-project/docs"` → **扩展池 1**：其他项目文档
- `"/opt/company-docs"` → **扩展池 2**：公司共享文档
- `"deny_roots"` → 禁止访问的目录（即使在 allow_roots 范围内）

### 步骤 3：验证配置

```bash
# 检查配置是否生效
curl http://localhost:8000/api/config/doc_access | jq .
```

**预期输出**：

```json
{
  "allow_roots": [
    "/Users/gavinzhang/ws-ai-recharge-2026/Yue",
    "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs",
    "/opt/company-docs"
  ],
  "deny_roots": [
    "/System",
    "/Library",
    "/Users/gavinzhang/ws-ai-recharge-2026/Yue/.git"
  ]
}
```

### 步骤 4：测试访问

**测试项目内文档（默认池）**：

```bash
curl -X POST http://localhost:8000/api/mcp/tools/docs_list \
  -H "Content-Type: application/json" \
  -d '{"root": "docs"}' | jq .
```

**测试项目外文档（扩展池）**：

```bash
curl -X POST http://localhost:8000/api/mcp/tools/docs_list \
  -H "Content-Type: application/json" \
  -d '{"root": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs"}' | jq .
```

---

## 🖥️ 方案二：前端 UI（简单）

### 步骤 1：打开设置界面

1. 打开 Yue 前端
2. 点击右上角设置图标 ⚙️
3. 选择 "System Configuration" 标签

### 步骤 2：配置 Allow Roots

在 "Allow Roots" 文本框中输入（**每行一个**）：

```
.
/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs
/opt/company-docs
```

### 步骤 3：配置 Deny Roots（可选）

在 "Deny Roots" 文本框中输入（**每行一个**）：

```
.git
node_modules
.venv
backend/data
```

### 步骤 4：保存

点击 "Save Document Access" 按钮

---

## 🔧 方案三：环境变量（适合容器化）

### 步骤 1：编辑 .env 文件

```bash
vim .env
```

### 步骤 2：添加配置

```bash
# 默认池 + 扩展池（逗号分隔）
DOC_ACCESS_ALLOW_ROOTS=.,/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs,/opt/company-docs

# 禁止访问的目录
DOC_ACCESS_DENY_ROOTS=.git,node_modules,.venv,backend/data
```

### 步骤 3：重启服务

```bash
# 停止服务
pkill -f "uvicorn"

# 重新启动
cd backend && uvicorn app.main:app --reload
```

**注意**：环境变量优先级 **高于** 配置文件

---

## 💬 使用示例

### 场景 1：访问项目内文档（默认池）

**聊天**：
```
你：请读取 docs/README.md 并总结

Agent: 好的，我来读取...
```

**API**：
```bash
curl -X POST http://localhost:8000/api/mcp/tools/docs_read \
  -H "Content-Type: application/json" \
  -d '{"path": "docs/README.md"}'
```

### 场景 2：访问项目外文档（扩展池）

**聊天**：
```
你：请读取 /Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/API.md

Agent: 好的，我来读取...
```

**API**：
```bash
curl -X POST http://localhost:8000/api/mcp/tools/docs_read \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/API.md"}'
```

### 场景 3：搜索多个目录

**聊天**：
```
你：在 /Users/gavinzhang/ws-ai-recharge-2026/other-project/docs 中搜索关于 API 的文档

Agent: 找到了以下相关文件...
```

---

## ✅ 验证清单

配置完成后，请检查：

- [ ] 配置文件语法正确
  ```bash
  jq . backend/data/global_config.json
  ```

- [ ] 配置已生效
  ```bash
  curl http://localhost:8000/api/config/doc_access | jq .
  ```

- [ ] 可以访问项目内文档（默认池）
  ```bash
  curl -X POST http://localhost:8000/api/mcp/tools/docs_read \
    -d '{"path": "docs/README.md"}'
  ```

- [ ] 可以访问项目外文档（扩展池）
  ```bash
  curl -X POST http://localhost:8000/api/mcp/tools/docs_read \
    -d '{"path": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/API.md"}'
  ```

- [ ] 禁止访问的目录已配置
  ```bash
  curl http://localhost:8000/api/config/doc_access | jq .deny_roots
  ```

---

## ⚠️ 常见问题

### Q1: 配置后不生效？

**解决方案**：
1. 检查 JSON 语法：`jq . backend/data/global_config.json`
2. 确认路径存在：`ls -la /Users/your-name/other-project/docs`
3. 重启服务：`pkill -f uvicorn && cd backend && uvicorn app.main:app --reload`

### Q2: 提示 "Path is outside allowed docs roots"？

**解决方案**：
1. 确认路径已添加到 `allow_roots`
2. 检查路径是否在 `deny_roots` 下
3. 使用绝对路径而非相对路径访问外部目录

### Q3: 可以只使用默认池，不配置扩展池吗？

**可以**！使用默认配置即可：

```json
{
  "doc_access": {
    "allow_roots": ["."]
  }
}
```

这样 Agent 只能访问当前项目内的文档。

### Q4: 扩展池最多可以配置几个？

**没有数量限制**！你可以根据需要添加任意多个：

```json
{
  "doc_access": {
    "allow_roots": [
      ".",
      "/path/to/dir1",
      "/path/to/dir2",
      "/path/to/dir3",
      ...
    ]
  }
}
```

---

## 📊 配置效果对比

| 配置项 | 路径 | 实际路径 | 可访问 | 可搜索 | 可读取 |
|--------|------|----------|--------|--------|--------|
| **默认池** | `.` | `/Users/.../Yue` | ✅ | ✅ | ✅ |
| **扩展池 1** | `/Users/.../other-project/docs` | `/Users/.../other-project/docs` | ✅ | ✅ | ✅ |
| **扩展池 2** | `/opt/company-docs` | `/opt/company-docs` | ✅ | ✅ | ✅ |

---

## 🔒 安全建议

### ✅ 推荐配置

```json
{
  "doc_access": {
    "allow_roots": [
      ".",
      "/Users/your-name/other-project/docs"
    ],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv",
      "backend/data"
    ]
  }
}
```

### ❌ 禁止配置

```json
{
  "doc_access": {
    "allow_roots": ["/"]  // 极度危险！允许访问整个文件系统
  }
}
```

---

## 📖 更多信息

- 详细配置文档：[DOCUMENT_ACCESS_CONFIG.md](DOCUMENT_ACCESS_CONFIG.md)
- 故障排查：[DOCUMENT_ACCESS_CONFIG.md#8-故障排查](DOCUMENT_ACCESS_CONFIG.md#8-故障排查)
- 安全最佳实践：[DOCUMENT_ACCESS_CONFIG.md#6-安全最佳实践](DOCUMENT_ACCESS_CONFIG.md#6-安全最佳实践)

---

**最后更新**: 2026-03-24
