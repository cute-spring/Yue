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

#### 后端
```bash
cd backend
python -m venv venv
source venv/bin/activate
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
- **后端**: FastAPI, Pydantic-AI, MCP SDK
- **前端**: SolidJS, TailwindCSS
- **工具**: Docker, npx

## 📁 目录结构
- `backend/`: FastAPI 后端逻辑与 Agent 定义
- `frontend/`: SolidJS 前端界面
- `data/`: 存放 Agent 配置与 MCP 配置
- `Dockerfile`: 用于容器化部署的配置文件
