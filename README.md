# Yue Agent Platform

这是一个基于 Pydantic-AI 和 FastAPI 构建的独立聊天机器人平台，支持多 LLM 提供商（DeepSeek, OpenAI, Zhipu）以及 Model Context Protocol (MCP) 工具集成。

## 🚀 快速启动

### 1. 环境初始化
项目提供了全自动的初始化脚本，会自动检查配置并安装所有依赖：
```bash
./setup.sh
```
> **注意**: 脚本会自动基于 `backend/.env.example` 创建 `backend/.env`。请务必编辑该文件填入你的 API Keys (如 `DEEPSEEK_API_KEY`)。

### 2. 本地运行

#### 开发模式 (推荐)
在前台同时启动前后端服务，并实时查看日志：
```bash
./dev.sh
```

#### 后台运行
将服务作为后台进程启动：
```bash
./start.sh
# 停止后台服务
./stop.sh
```

### 3. 代码质量检查
在提交代码前，建议运行全栈检查（包含后端测试与前端类型检查）：
```bash
./check.sh
```

---

## 🛠️ 脚本说明 (CLI Tools)
项目根目录下提供了以下实用工具脚本：

| 脚本 | 功能描述 |
| :--- | :--- |
| `setup.sh` | **初始化**: 自动创建 `.env` 并安装前后端依赖。 |
| `dev.sh` | **开发模式**: 前台启动服务，实时输出日志，支持 `Ctrl+C` 退出。 |
| `start.sh` | **后台启动**: 增强版启动脚本，支持进程自愈与日志重定向。 |
| `stop.sh` | **停止服务**: 深度清理后台进程，确保无残留。 |
| `check.sh` | **质量门禁**: 自动运行 Pytest (后端) 与 TSC/Vitest (前端)。 |
| `clean.sh` | **环境清理**: 深度删除 `node_modules`, `.venv` 及各种缓存。 |
| `install_deps.sh`| **依赖安装**: 仅执行依赖检查与安装。 |
| `deploy_docker.sh`| **Docker 部署**: 一键构建并启动容器。 |

## 🛠️ 技术栈
- **后端**: FastAPI, Pydantic-AI, MCP SDK, SQLite (Pydantic AI 集成)
- **前端**: SolidJS, TailwindCSS, Marked.js, Highlight.js
- **主题**: Emerald Green (翡翠绿) 设计系统

## ✨ 核心特性
- **三栏式布局**: 侧边栏 (图标轨/全宽) + 主聊天区 + 智能知识面板。
- **多模型驱动**: 支持 OpenAI, DeepSeek, 智谱, 以及本地 Ollama 模型。
- **MCP 工具集成**: 插件化工具调用，支持 Filesystem 等多种协议。
- **本地文档检索**: 专门的文档检索 Agent，支持安全可控的本地目录 Markdown 搜索与溯源。
- **深度思考 UI**: 完美适配 DeepSeek R1 的推理过程展示。
- **响应式设计**: 完美适配桌面、平板与移动端。

## 📁 目录结构
- `backend/`: FastAPI 后端逻辑、Agent 定义与 SQLite 数据库
- `frontend/`: SolidJS 前端界面与 Emerald 主题配置
- `data/`: 存放 Agent 配置与 MCP 配置
- `docs/`: 项目开发文档（特性、需求、路线图、测试、UI 设计指南等）
- `Dockerfile`: 用于容器化部署的配置文件
