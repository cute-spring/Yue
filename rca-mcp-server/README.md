# RCA-Expert MCP Server

> **衔接经典软件工程与现代 AI 辅助开发的根因分析专家。**

这是一个独立的根因分析（RCA）与解决方案知识库 MCP 服务器。它可以被集成到任何支持 MCP 协议的 AI 客户端中（如 Trae, Claude Desktop, Cursor 等），帮助开发团队沉淀技术资产，避免“在同一个坑里跌倒两次”。

---

## 🏗️ 系统架构

```mermaid
graph LR
    A[AI Agent / IDE] -- MCP Protocol --> B[RCA-Expert Server]
    B -- CRUD --> C[(JSON Knowledge Base)]
    B -- Search/Rank --> C
```

## 🚀 核心功能

- **🛠️ 自动化问题记录 (`record_rca`)**：捕获开发过程中的意外问题、根本原因、修复方案及预防措施。支持标签分类与代码变更追踪。
- **🔍 智能方案检索 (`search_rca`)**：基于加权搜索算法（标签 > 描述 > 根因），为当前遇到的难题提供精准的历史修复建议。
- **📊 可视化报告生成 (`generate_rca_report`)**：生成专业的 Markdown 分析报告或知识库摘要，便于团队分享与回顾。

---

## 📋 环境要求

- **Python**: 3.10+
- **MCP SDK**: `fastmcp`
- **存储**: 本地 JSON 文件（默认），无需数据库。

## 📦 安装与配置

### 1. 快速开始
```bash
# 克隆仓库
git clone https://github.com/your-username/rca-mcp-server.git
cd rca-mcp-server

# 安装依赖
pip install -e .
```

### 2. 存储配置 (可选)
默认知识库路径为 `./data/knowledge_base.json`。
可以通过环境变量灵活切换不同项目的知识库：
```bash
export RCA_STORAGE_PATH="/path/to/project_specific_kb.json"
```

---

## 🛠️ IDE 集成指南

### 在 Trae / Claude Desktop 中配置
1. 找到 MCP 配置文件（如 `mcp_configs.json` 或 IDE 设置面板）。
2. 添加以下配置：

```json
{
  "mcpServers": {
    "rca-expert": {
      "command": "python3",
      "args": ["/绝对路径/rca-mcp-server/src/rca_server.py"],
      "env": {
        "RCA_STORAGE_PATH": "/你的存储路径/kb.json"
      }
    }
  }
}
```

---

## 📖 使用场景与指令示例

| 场景 | 你可以对 AI 说... | 调用工具 |
| :--- | :--- | :--- |
| **记录 Bug** | “记录一下刚才解决的 Token 溢出 Bug 的 RCA。” | `record_rca` |
| **寻求建议** | “我遇到了 API 401 错误，历史记录里有类似方案吗？” | `search_rca` |
| **复盘周报** | “生成本周记录的所有 RCA 摘要报告。” | `generate_rca_report` |

---

## 🛡️ 数据隐私
- **全本地化**：所有 RCA 记录均存储在你指定的本地 JSON 文件中。
- **无外部上报**：除与你本地 IDE 通信外，不与任何第三方服务器交换数据。

## ⚖️ 协议
[MIT License](LICENSE)
