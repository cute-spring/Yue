# Yue Agent Platform

这是一个基于 Pydantic-AI 和 FastAPI 构建的独立聊天机器人平台，支持多 LLM 提供商（DeepSeek, OpenAI, Zhipu）以及 Model Context Protocol (MCP) 工具集成。

## 🚀 快速启动

### 1. 准备配置
在 `backend` 目录下创建 `.env` 文件：
```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 并填入你的 API Keys
```

### 2. 本地开发运行

#### 一键启动
项目提供了便捷的脚本来同时启动前后端服务：
```bash
./start.sh
```
要停止所有服务，可以运行：
```bash
./stop.sh
```

#### 分步启动 (可选)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

### 3. Docker 部署
项目支持一键 Docker 化部署：
```bash
cd Yue
docker build -t yue-agent .
docker run -p 8000:8000 --env-file backend/.env yue-agent
```

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
