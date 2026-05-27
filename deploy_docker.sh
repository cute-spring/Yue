#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 开始 Yue Agent Platform Docker 部署流程...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
YUE_DIR="$WORKSPACE_ROOT/Yue"

# 1. 检查 Docker 环境
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Docker，请先安装 Docker Desktop。${NC}"
    exit 1
fi

# 2. 检查配置文件
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  未找到 backend/.env 配置文件。${NC}"
    if [ -f "backend/.env.example" ]; then
        echo -e "${YELLOW}📄 正在从 .env.example 创建默认配置文件...${NC}"
        cp backend/.env.example backend/.env
        echo -e "${RED}❗ 请注意：请立即编辑 backend/.env 文件并填入您的 API Keys (如 DEEPSEEK_API_KEY)，否则服务无法正常工作。${NC}"
        read -p "按回车键确认已了解，或按 Ctrl+C 中止..."
    else
        echo -e "${RED}❌ 缺少 backend/.env.example 模板文件，无法创建配置。${NC}"
        exit 1
    fi
fi

# 3. 构建镜像
echo -e "${GREEN}📦 正在构建 Docker 镜像 (yue-agent)... 这可能需要几分钟。${NC}"
cd "$WORKSPACE_ROOT"
docker build -f Yue/Dockerfile -t yue-agent .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 镜像构建失败。请检查网络连接或 Dockerfile。${NC}"
    exit 1
fi

# 4. 清理旧容器
if [ "$(docker ps -aq -f name=yue-agent)" ]; then
    echo -e "${YELLOW}🗑️  发现旧容器，正在停止并删除...${NC}"
    docker stop yue-agent >/dev/null 2>&1
    docker rm yue-agent >/dev/null 2>&1
fi

# 5. 启动容器
echo -e "${GREEN}▶️  正在启动新容器...${NC}"
docker run -d \
  --name yue-agent \
  -p 8000:8000 \
  --env-file "$YUE_DIR/backend/.env" \
  --restart unless-stopped \
  yue-agent

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 部署成功！${NC}"
    echo -e "🌍 访问地址: ${GREEN}http://localhost:8000${NC}"
    echo -e "📝 查看日志: ${YELLOW}docker logs -f yue-agent${NC}"
else
    echo -e "${RED}❌ 容器启动失败。${NC}"
    exit 1
fi
