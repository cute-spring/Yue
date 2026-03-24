# Document Access 配置手册

本文档详细介绍如何配置 Yue 系统的文档访问控制（Document Access Control），确保 AI Agent 能够安全地访问本地文件。

## 目录

- [1. 概述](#1-概述)
- [2. 核心概念](#2-核心概念)
- [3. 配置方式](#3-配置方式)
- [4. Allow Roots 配置详解](#4-allow-roots-配置详解)
- [5. Deny Roots 配置详解](#5-deny-roots-配置详解)
- [6. 安全最佳实践](#6-安全最佳实践)
- [7. 常见场景配置示例](#7-常见场景配置示例)
  - [7.1 场景 1：纯文档问答（最安全）](#71-场景 1 纯文档问答最安全)
  - [7.2 场景 2：开发环境 - 访问项目外其他目录（重点）⭐](#72-场景 2 开发环境 - 访问项目外其他目录重点)
  - [7.3 场景 3：代码辅助开发](#73-场景 3 代码辅助开发)
  - [7.4 场景 4：多项目共享文档](#74-场景 4 多项目共享文档)
  - [7.5 快速上手指南：5 分钟配置外部目录访问](#75-快速上手指南 5 分钟配置外部目录访问)
- [8. 故障排查](#8-故障排查)

---

## 🚀 快速参考（30 秒找到你需要的）

### 我想访问项目外的其他目录，怎么配置？

**答案**：在 `backend/data/global_config.json` 中添加绝对路径到 `allow_roots`：

```json
{
  "doc_access": {
    "allow_roots": [
      "docs",
      "/Users/your-name/other-project/docs",  // 其他项目
      "/opt/company-docs"                     // 公司共享文档
    ]
  }
}
```

**详细说明**：[场景 2：开发环境 - 访问项目外其他目录](#72-场景 2-开发环境 - 访问项目外其他目录重点) ⭐

### 我想快速上手，有教程吗？

**答案**：有！直接跳转到 [快速上手指南：5 分钟配置外部目录访问](#75-快速上手指南 -5-分钟配置外部目录访问)

### 配置后不生效怎么办？

**答案**：查看 [故障排查](#8-故障排查) 章节

### 支持哪些路径格式？

- ✅ **相对路径**：`docs`, `backend/app`（相对于项目根目录）
- ✅ **绝对路径**：`/Users/name/docs`, `/opt/company-docs`
- ✅ **上级目录**：`../other-project/docs`（谨慎使用）
- ❌ **禁止**：`/`（根目录，极度危险）

### 配置优先级是怎样的？

```
环境变量 > 配置文件 > 默认值
```

**示例**：
- 环境变量设置了 `DOC_ACCESS_ALLOW_ROOTS=backend`
- 配置文件设置了 `allow_roots: ["docs"]`
- **最终生效**：`["backend"]`（环境变量覆盖）

---

## 1. 概述

### 1.1 什么是 Document Access Control？

Document Access Control 是 Yue 系统的安全机制，用于**限制 AI Agent 可以访问的文件和目录范围**。通过配置白名单（Allow Roots）和黑名单（Deny Roots），您可以精确控制 Agent 的文件访问权限。

### 1.2 为什么需要配置？

- **防止数据泄露**：避免 Agent 读取敏感文件（如 `.env`、源代码、配置文件）
- **最小权限原则**：只授予 Agent 完成工作所需的最小访问权限
- **防御提示词攻击**：即使用户尝试恶意提示，Agent 也无法访问禁止的文件
- **合规要求**：满足企业安全审计和访问控制要求

### 1.3 工作原理

```
用户请求：读取文件 docs/guide.md
         ↓
检查路径是否在 Allow Roots 下
         ↓
    ┌────┴────┐
    ↓         ↓
  ✅ 是      ❌ 否
    ↓         ↓
检查是否在 Deny Roots 下   拒绝访问
    ↓
┌───┴───┐
↓       ↓
✅ 否   ❌ 是
↓       ↓
允许访问  拒绝访问
```

---

## 2. 核心概念

### 2.1 Allow Roots（允许访问的根目录）

**定义**：白名单机制，指定 Agent **可以访问**的目录列表。

**特点**：
- 支持相对路径和绝对路径
- 支持多个目录
- 未配置时默认值为 `["."]`（项目根目录）
- **路径检查基于 realpath**，防止 symlink 逃逸

**示例**：
```json
{
  "allow_roots": ["docs", "/opt/shared-docs", "../other-project/docs"]
}
```

### 2.2 Deny Roots（禁止访问的根目录）

**定义**：黑名单机制，指定**即使在 Allow Roots 范围内也禁止访问**的目录。

**特点**：
- 优先级高于 Allow Roots
- 系统自动添加操作系统级别的保护目录
- 推荐配置常见的敏感目录

**系统默认保护**（无需配置）：
- **macOS**: `/System`, `/Library`
- **Linux**: `/etc`, `/proc`, `/sys`, `/dev`

**用户推荐配置**：
```json
{
  "deny_roots": [
    ".git",
    "node_modules",
    ".venv",
    "backend/data",
    "__pycache__",
    "dist",
    "build"
  ]
}
```

### 2.3 路径解析规则

1. **相对路径**：相对于项目根目录解析
   - `"docs"` → `/Users/your-name/Yue/docs`
   - `"."` → `/Users/your-name/Yue`

2. **绝对路径**：直接使用完整路径
   - `"/opt/shared-docs"` → `/opt/shared-docs`

3. **路径规范化**：所有路径都会通过 `realpath` 规范化，解析 symlink

4. **子目录继承**：允许访问根目录下的所有子目录
   - 允许 `docs` → 可以访问 `docs/guide.md`、`docs/api/v1.md` 等

---

## 3. 配置方式

### 3.1 方式一：配置文件（推荐）

**文件位置**：`backend/data/global_config.json`

**步骤**：

1. 编辑配置文件：
```bash
# 从项目根目录执行
vim backend/data/global_config.json
```

2. 添加或修改 `doc_access` 部分：
```json
{
  "doc_access": {
    "allow_roots": ["docs"],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv"
    ]
  }
}
```

3. 保存后生效（无需重启服务）

**优点**：
- 配置持久化
- 版本可控
- 易于备份和恢复

### 3.2 方式二：环境变量

**环境变量名**：
- `DOC_ACCESS_ALLOW_ROOTS`：设置允许目录
- `DOC_ACCESS_DENY_ROOTS`：设置禁止目录

**格式**：逗号分隔的列表

**步骤**：

1. 编辑 `.env` 文件：
```bash
vim .env
```

2. 添加配置：
```bash
DOC_ACCESS_ALLOW_ROOTS=docs,/opt/shared-docs
DOC_ACCESS_DENY_ROOTS=.git,node_modules,.venv
```

3. 重启后端服务

**优先级**：环境变量 **覆盖** 配置文件

**优点**：
- 适合容器化部署
- 便于 CI/CD 集成
- 不同环境使用不同配置

### 3.3 方式三：前端界面

**路径**：Settings → System Configuration → Document Access

**步骤**：

1. 打开 Yue 前端界面
2. 点击右上角设置图标
3. 选择 "System Configuration" 标签
4. 滚动到 "Document Access" 部分
5. 在 "Allow Roots" 文本框中输入目录（每行一个）
6. 在 "Deny Roots" 文本框中输入目录（每行一个）
7. 点击 "Save Document Access" 按钮

**优点**：
- 图形化界面，操作简单
- 实时查看生效的配置数量
- 适合快速调整

### 3.4 配置优先级

```
环境变量 > 配置文件 > 默认值
```

**示例场景**：
- 配置文件中 `allow_roots: ["docs"]`
- 环境变量中 `DOC_ACCESS_ALLOW_ROOTS=backend`
- **最终生效**：`["backend"]`（环境变量覆盖配置文件）

---

## 4. Allow Roots 配置详解

### 4.1 基本语法

```json
{
  "allow_roots": ["路径 1", "路径 2", "路径 3"]
}
```

### 4.2 路径格式

#### 相对路径（推荐）

相对于项目根目录：

```json
{
  "allow_roots": [
    "docs",              // 项目 docs 目录
    "backend/app",       // 后端代码目录
    "../shared-docs"     // 上级目录的共享文档
  ]
}
```

**优点**：
- 配置可移植
- 不依赖具体机器路径
- 适合团队协作

#### 绝对路径

完整的文件系统路径：

```json
{
  "allow_roots": [
    "/opt/yue/docs",
    "/Users/your-name/projects/yue/docs",
    "/mnt/shared/documents"
  ]
}
```

**适用场景**：
- 跨设备挂载的目录
- 生产环境固定路径
- 多项目共享目录

### 4.3 多目录配置

支持配置多个允许目录，Agent 可以访问所有这些目录：

```json
{
  "allow_roots": [
    "docs",              // 项目文档
    "backend/src",       // 后端源码
    "frontend/src",      // 前端源码
    "/opt/api-docs"      // 外部 API 文档
  ]
}
```

**访问规则**：
- ✅ 可以访问 `docs/guide.md`
- ✅ 可以访问 `backend/src/main.py`
- ✅ 可以访问 `frontend/src/App.tsx`
- ✅ 可以访问 `/opt/api-docs/openapi.yaml`
- ❌ 无法访问 `backend/tests/`（不在允许列表）

### 4.4 特殊路径说明

| 路径 | 含义 | 说明 |
|------|------|------|
| `.` | 项目根目录 | 允许访问整个项目 |
| `..` | 上级目录 | 允许访问项目父目录（谨慎使用） |
| `docs` | docs 子目录 | 仅允许访问 docs 目录 |
| `/` | 根目录 | **极度危险**，允许访问整个文件系统 |

**⚠️ 警告**：
- **不要**设置 `allow_roots: ["/"]`
- **不要**设置 `allow_roots: [".."]` 除非绝对必要
- **推荐**使用最小必要范围，如 `["docs"]`

### 4.5 路径验证

配置后，系统会自动验证：

1. **路径存在性检查**：路径必须存在（或父目录存在）
2. **绝对路径转换**：相对路径转为绝对路径
3. **realpath 规范化**：解析 symlink
4. **系统保护检查**：不能与系统默认 deny roots 冲突

**验证命令**：
```bash
# 检查配置是否生效
curl http://localhost:8000/api/config/doc_access
```

**响应示例**：
```json
{
  "allow_roots": [
    "/Users/your-name/Yue/docs"
  ],
  "deny_roots": [
    "/System",
    "/Library",
    "/Users/your-name/Yue/.git"
  ]
}
```

---

## 5. Deny Roots 配置详解

### 5.1 基本语法

```json
{
  "deny_roots": ["路径 1", "路径 2", "路径 3"]
}
```

### 5.2 系统默认保护

系统会根据操作系统自动添加保护目录：

**macOS**：
```json
["/System", "/Library"]
```

**Linux**：
```json
["/etc", "/proc", "/sys", "/dev"]
```

**Windows**（未来支持）：
```json
["C:\\Windows", "C:\\Program Files"]
```

### 5.3 推荐用户配置

**基础安全配置**（推荐所有环境）：
```json
{
  "deny_roots": [
    ".git",              // Git 版本控制
    "node_modules",      // NPM 依赖
    ".venv",             // Python 虚拟环境
    "venv",
    "__pycache__",       // Python 缓存
    ".pytest_cache",
    ".idea",             // IDE 配置
    ".vscode"
  ]
}
```

**生产环境增强**：
```json
{
  "deny_roots": [
    ".git",
    "node_modules",
    ".venv",
    "backend/data",      // 后端数据目录
    "data",              // 项目数据目录
    "dist",              // 构建产物
    "build",
    "target",
    "vendor",
    "pods"
  ]
}
```

### 5.4 优先级规则

Deny Roots 的优先级 **高于** Allow Roots：

**示例**：
```json
{
  "allow_roots": ["/Users/your-name/Yue"],
  "deny_roots": ["/Users/your-name/Yue/.git"]
}
```

**结果**：
- ✅ 可以访问 `/Users/your-name/Yue/docs/guide.md`
- ❌ 无法访问 `/Users/your-name/Yue/.git/config`（即使 `.git` 在 allow_roots 下）

### 5.5 路径匹配规则

1. **精确匹配**：路径完全匹配
2. **前缀匹配**：路径在 deny root 下
3. **realpath 匹配**：基于真实路径（防止 symlink 绕过）

**示例**：
```json
{
  "deny_roots": [".git"]
}
```

**匹配结果**：
- ❌ `.git/config` ✅ 被拒绝
- ❌ `backend/.git/config` ✅ 被拒绝
- ❌ `docs/.gitignore` ✅ 被拒绝（`.gitignore` 不在 `.git` 下，**允许访问**）

**注意**：`.git` 只匹配 `.git` 目录及其子目录，不匹配 `.gitignore` 等文件。

---

## 6. 安全最佳实践

### 6.1 最小权限原则

**❌ 不推荐**：
```json
{
  "allow_roots": ["."]  // 允许整个项目
}
```

**✅ 推荐**：
```json
{
  "allow_roots": ["docs"],  // 仅允许文档目录
  "deny_roots": [
    ".git",
    "node_modules",
    ".venv",
    "backend/data"
  ]
}
```

### 6.2 敏感文件保护

**问题**：Allow Roots 无法阻止访问 `.env` 等敏感文件

**解决方案 1**：使用 Deny Roots 排除包含敏感文件的目录
```json
{
  "allow_roots": ["docs"],
  "deny_roots": ["backend/data"]  // 包含 .env 的目录
}
```

**解决方案 2**：将敏感文件移到 Allow Roots 之外
```
项目结构：
├── docs/           ✅ 允许访问
├── backend/
│   ├── app/        ✅ 允许访问
│   └── secrets/    ❌ 不允许访问（包含 .env）
```

**解决方案 3**：使用文件级保护（Phase 0 计划中）
```python
# 未来功能：自动阻止特定文件名
DENIED_FILENAMES = {".env", ".gitconfig", "id_rsa"}
```

### 6.3 环境隔离

**开发环境**（宽松）：
```json
{
  "allow_roots": [".", "../other-project"],
  "deny_roots": [".git", "node_modules"],
  "enable_audit_logging": false
}
```

**生产环境**（严格）：
```json
{
  "allow_roots": ["/opt/yue/docs"],
  "deny_roots": [
    ".git",
    "node_modules",
    ".venv",
    "backend/data"
  ],
  "enable_audit_logging": true
}
```

### 6.4 审计日志

**启用审计**（推荐生产环境）：
```json
{
  "doc_access": {
    "enable_audit_logging": true,
    "log_level": "info"
  }
}
```

**审计内容**：
- 访问的文件路径
- 访问操作类型（read/list/search）
- 访问结果（允许/拒绝）
- 拒绝原因

### 6.5 定期检查清单

- [ ] `allow_roots` 是否是最小必要范围
- [ ] `deny_roots` 是否包含所有敏感目录
- [ ] 是否有 `.env` 文件在允许范围内
- [ ] 审计日志是否正常记录
- [ ] 是否有异常的访问拒绝
- [ ] 配置是否已版本控制

---

## 7. 常见场景配置示例

### 7.1 场景 1：纯文档问答（最安全）

**需求**：Agent 只能读取 `docs/` 目录下的文档

**配置**：
```json
{
  "doc_access": {
    "allow_roots": ["docs"],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv"
    ]
  }
}
```

**效果**：
- ✅ 可以访问：`docs/guide.md`, `docs/api.md`
- ❌ 无法访问：`backend/app.py`, `.env`, `package.json`

### 7.2 场景 2：开发环境 - 访问项目外其他目录（重点）⭐

**需求**：在本地开发时，需要访问项目以外的其他目录，例如：
- 其他项目的文档目录
- 公司共享文档库
- NAS/网络存储的文档
- 个人笔记目录

**配置方法（3 种任选其一）**：

#### 方法 1：配置文件（推荐）

编辑 `backend/data/global_config.json`：

```json
{
  "doc_access": {
    "allow_roots": [
      "docs",
      "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs",
      "/opt/company-docs",
      "/Volumes/nas/team-docs",
      "/Users/gavinzhang/notes/tech-docs"
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

**详细说明**：
- `"docs"`：当前项目的 docs 目录（相对路径）
- `"/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs"`：其他项目的文档（绝对路径）
- `"/opt/company-docs"`：公司共享文档（绝对路径）
- `"/Volumes/nas/team-docs"`：NAS 网络存储（绝对路径）
- `"/Users/gavinzhang/notes/tech-docs"`：个人笔记（绝对路径）

**验证配置**：
```bash
# 1. 查看配置是否生效
curl http://localhost:8000/api/config/doc_access | jq .

# 2. 测试访问外部目录
curl http://localhost:8000/api/mcp/tools/docs_list \
  -d '{"root": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs"}'

# 3. 测试读取外部目录文件
curl http://localhost:8000/api/mcp/tools/docs_read \
  -d '{"path": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/README.md"}'
```

**效果**：
- ✅ 可以访问：当前项目 docs + 所有配置的外部目录
- ✅ 可以跨项目读取文档
- ✅ 可以访问 NAS/网络存储
- ❌ 无法访问：未配置的其他目录

#### 方法 2：前端 UI 配置

1. 打开 Yue 前端界面
2. 点击右上角设置图标 ⚙️
3. 选择 "System Configuration" 标签
4. 滚动到 "Document Access" 部分
5. 在 "Allow Roots" 文本框中输入（每行一个）：
```
docs
/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs
/opt/company-docs
/Volumes/nas/team-docs
```
6. 点击 "Save Document Access" 按钮

**优点**：
- 图形化界面，操作简单
- 实时查看生效的配置数量
- 无需编辑配置文件

**缺点**：
- 配置保存在浏览器本地
- 重启浏览器后可能丢失

#### 方法 3：环境变量（适合容器化部署）

编辑 `.env` 文件：

```bash
# 相对路径（项目内）
DOC_ACCESS_ALLOW_ROOTS=docs,/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs,/opt/company-docs

# 或者使用 JSON 数组格式
DOC_ACCESS_ALLOW_ROOTS=["docs","/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs","/opt/company-docs"]
```

**重启后端服务**：
```bash
# 停止服务
pkill -f "uvicorn"

# 重新启动
cd backend && uvicorn app.main:app --reload
```

**注意事项**：
- ⚠️ 环境变量优先级 **高于** 配置文件
- ⚠️ 修改后需要重启服务
- ✅ 适合 CI/CD 和容器化部署

### 7.3 场景 3：代码辅助开发

**需求**：Agent 需要读取源代码和文档

**配置**：
```json
{
  "doc_access": {
    "allow_roots": ["docs", "backend/app", "frontend/src"],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv",
      "backend/data",
      "__pycache__"
    ]
  }
}
```

**效果**：
- ✅ 可以访问：源代码、文档
- ❌ 无法访问：依赖库、数据文件、构建产物

### 7.4 场景 4：多项目共享文档

**需求**：访问当前项目和外部共享文档库

**配置**：
```json
{
  "doc_access": {
    "allow_roots": [
      "docs",
      "../shared-docs",
      "/opt/company-docs"
    ],
    "deny_roots": [
      ".git",
      "node_modules"
    ]
  }
}
```

**效果**：
- ✅ 可以访问：当前项目 docs、共享文档库、公司文档服务器
- ❌ 无法访问：其他项目目录

### 7.4 场景 4：生产环境部署

**需求**：严格限制访问范围，启用审计

**配置**：
```json
{
  "doc_access": {
    "allow_roots": ["/opt/yue/docs"],
    "deny_roots": [
      "/opt/yue/.git",
      "/opt/yue/backend/data",
      "/opt/yue/node_modules"
    ],
    "security_mode": "strict",
    "enable_audit_logging": true
  }
}
```

**效果**：
- ✅ 严格限制在指定目录
- ✅ 所有访问记录到审计日志
- ✅ 防止路径穿越攻击

### 7.5 场景 5：开发环境（宽松模式）

**需求**：快速开发，需要访问多个目录

**配置**：
```json
{
  "doc_access": {
    "allow_roots": ["."],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv",
      "dist",
      "build"
    ],
    "security_mode": "permissive"
  }
}
```

**⚠️ 警告**：此配置允许访问整个项目，仅用于开发环境！

### 7.6 场景 6：多租户部署

**需求**：不同 Agent 访问不同目录

**配置**：
```json
{
  "doc_access": {
    "allow_roots": [
      "/tenants/tenant-a/docs",
      "/tenants/tenant-b/docs"
    ],
    "deny_roots": [
      "/tenants/tenant-a/.git",
      "/tenants/tenant-b/.git"
    ],
    "agent_overrides": {
      "tenant-a-agent": {
        "allow_roots": ["/tenants/tenant-a/docs"]
      },
      "tenant-b-agent": {
        "allow_roots": ["/tenants/tenant-b/docs"]
      }
    }
  }
}
```

**效果**：
- ✅ 租户 A 的 Agent 只能访问租户 A 的文档
- ✅ 租户 B 的 Agent 只能访问租户 B 的文档
- ✅ 数据隔离，互不干扰

---

## 7.5 快速上手指南：5 分钟配置外部目录访问

**目标**：让 Agent 能够访问你本地其他项目的文档

### 步骤 1：确定要访问的目录

假设你有以下目录结构：
```
/Users/gavinzhang/
├── ws-ai-recharge-2026/
│   └── Yue/                    # 当前项目
│       ├── docs/               # 当前项目文档
│       └── backend/
├── other-project/
│   └── docs/                   # 其他项目文档 ✅ 想访问
└── notes/
    └── tech-docs/              # 个人笔记 ✅ 想访问
```

### 步骤 2：编辑配置文件

**方式 A：直接编辑（推荐）**

```bash
# 在项目根目录执行
vim backend/data/global_config.json
```

添加或修改 `doc_access` 部分：

```json
{
  "doc_access": {
    "allow_roots": [
      "docs",
      "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs",
      "/Users/gavinzhang/notes/tech-docs"
    ],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv"
    ]
  }
}
```

**方式 B：使用配置文件模板**

如果 `backend/data/global_config.json` 不存在，从模板复制：

```bash
cp backend/data/global_config.json.example backend/data/global_config.json
```

然后编辑新文件。

### 步骤 3：验证配置

**1. 检查配置是否生效**：

```bash
curl http://localhost:8000/api/config/doc_access | jq .
```

**预期输出**：
```json
{
  "allow_roots": [
    "/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs",
    "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs",
    "/Users/gavinzhang/notes/tech-docs"
  ],
  "deny_roots": [
    "/System",
    "/Library",
    "/Users/gavinzhang/ws-ai-recharge-2026/Yue/.git"
  ]
}
```

**2. 测试访问外部目录**：

```bash
# 列出外部目录的文件
curl -X POST http://localhost:8000/api/mcp/tools/docs_list \
  -H "Content-Type: application/json" \
  -d '{
    "root": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs"
  }' | jq .
```

**预期输出**：
```json
{
  "files": [
    "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/README.md",
    "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/guide.md"
  ]
}
```

**3. 测试读取外部文件**：

```bash
# 读取外部目录的具体文件
curl -X POST http://localhost:8000/api/mcp/tools/docs_read \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/README.md"
  }' | jq .
```

**预期输出**：
```json
{
  "content": "# Other Project\n\nThis is the README...",
  "path": "/Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/README.md"
}
```

### 步骤 4：在聊天中使用

现在你可以在聊天中直接让 Agent 访问外部目录的文件：

**示例对话**：
```
你：请读取 /Users/gavinzhang/ws-ai-recharge-2026/other-project/docs/README.md 并总结

Agent: 好的，我来读取这个文件...
[成功读取并总结]
```

**或者搜索外部目录**：
```
你：在 /Users/gavinzhang/ws-ai-recharge-2026/other-project/docs 中搜索关于 API 的文档

Agent: 找到了以下相关文件...
[列出搜索结果]
```

### 常见问题

**Q1: 配置后不生效？**
- 检查 JSON 语法是否正确
- 确认路径存在：`ls -la /Users/gavinzhang/ws-ai-recharge-2026/other-project/docs`
- 重启后端服务：`pkill -f uvicorn && cd backend && uvicorn app.main:app --reload`

**Q2: 提示 "Path is outside allowed docs roots"？**
- 确认路径已添加到 `allow_roots`
- 检查路径是否在 `deny_roots` 下
- 使用绝对路径而非相对路径

**Q3: 可以访问相对路径吗？**
- 可以，但推荐使用绝对路径访问外部目录
- 相对路径会自动转为项目根目录的绝对路径

---

## 8. 故障排查

### 8.1 问题：无法访问预期目录

**症状**：Agent 报告 "Path is outside allowed docs roots"

**排查步骤**：

1. **检查配置是否生效**：
```bash
curl http://localhost:8000/api/config/doc_access
```

2. **验证路径是否在 Allow Roots 下**：
```bash
# 查看实际解析的路径
realpath docs/guide.md
# 对比 allow_roots 中的路径
```

3. **检查是否有 Deny Roots 冲突**：
```bash
# 查看 deny_roots 列表
curl http://localhost:8000/api/config/doc_access | jq .deny_roots
```

4. **检查文件权限**：
```bash
ls -la docs/guide.md
```

**解决方案**：
- 将目录添加到 `allow_roots`
- 从 `deny_roots` 中移除（如果冲突）
- 修复文件权限

### 8.2 问题：配置不生效

**症状**：修改配置后，访问控制没有变化

**排查步骤**：

1. **检查配置优先级**：
```bash
# 环境变量可能覆盖配置文件
echo $DOC_ACCESS_ALLOW_ROOTS
```

2. **检查配置文件语法**：
```bash
# 验证 JSON 格式
jq . backend/data/global_config.json
```

3. **重启后端服务**：
```bash
# 停止服务
pkill -f "uvicorn"
# 重新启动
cd backend && uvicorn app.main:app --reload
```

**解决方案**：
- 移除或修改环境变量
- 修复 JSON 语法错误
- 重启服务

### 8.3 问题：审计日志没有记录

**症状**：启用了审计日志，但没有看到日志

**排查步骤**：

1. **检查配置**：
```json
{
  "doc_access": {
    "enable_audit_logging": true
  }
}
```

2. **检查日志级别**：
```bash
# 查看日志配置
grep -A 5 "logging" backend/data/global_config.json
```

3. **查看日志输出**：
```bash
# 查看后端日志
tail -f backend/logs/app.log
# 或查看标准输出（如果使用 stdout）
```

**解决方案**：
- 启用 `enable_audit_logging`
- 调整日志级别为 `info`
- 检查日志输出位置

### 8.4 问题：性能下降

**症状**：启用审计日志后，响应变慢

**排查步骤**：

1. **检查日志量**：
```bash
# 查看日志文件大小
ls -lh backend/logs/app.log
```

2. **检查磁盘 I/O**：
```bash
iostat -x 1
```

**解决方案**：
- 启用日志轮转（log rotation）
- 降低日志级别为 `warning`
- 使用异步日志
- 考虑关闭审计（仅开发环境）

### 8.5 常见错误信息

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Root is outside allowed docs roots` | 路径不在 allow_roots 下 | 添加路径到 allow_roots |
| `Root is under denied paths` | 路径在 deny_roots 下 | 从 deny_roots 移除或修改路径 |
| `Path is outside allowed docs roots` | 文件路径不在允许范围 | 检查文件是否在 allow_roots 子目录下 |
| `Invalid path` | 路径不存在或格式错误 | 检查路径是否正确 |

---

## 附录 A：配置模板

### A.1 最小安全配置（推荐）

```json
{
  "doc_access": {
    "allow_roots": ["docs"],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv",
      "__pycache__"
    ]
  }
}
```

### A.2 开发环境配置

```json
{
  "doc_access": {
    "allow_roots": [".", "backend/app", "frontend/src"],
    "deny_roots": [
      ".git",
      "node_modules",
      ".venv",
      "dist",
      "build"
    ],
    "security_mode": "permissive",
    "enable_audit_logging": false
  }
}
```

### A.3 生产环境配置

```json
{
  "doc_access": {
    "allow_roots": ["/opt/yue/docs"],
    "deny_roots": [
      "/opt/yue/.git",
      "/opt/yue/backend/data",
      "/opt/yue/node_modules"
    ],
    "security_mode": "strict",
    "enable_audit_logging": true,
    "audit_log_level": "info"
  }
}
```

---

## 附录 B：快速参考卡片

### 路径格式速查

```
相对路径：docs, backend/app, ../shared
绝对路径：/opt/docs, /Users/name/project/docs
特殊路径：. (当前), .. (上级) - 谨慎使用
```

### 配置优先级速查

```
环境变量 > 配置文件 > 默认值
```

### 安全检查清单

```
□ allow_roots 是最小必要范围
□ deny_roots 包含所有敏感目录
□ .env 文件在允许范围外
□ 审计日志已启用（生产环境）
□ 配置已版本控制
```

### 常用命令

```bash
# 查看当前配置
curl http://localhost:8000/api/config/doc_access

# 测试文件访问
curl http://localhost:8000/api/mcp/tools/docs_read \
  -d '{"path": "docs/guide.md"}'

# 查看审计日志
tail -f backend/logs/app.log | grep doc_access
```

---

## 更新日志

- **2026-03-24**：初始版本，包含完整的配置指南和故障排查
