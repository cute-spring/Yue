#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}🚀 Initializing Yue Agent Platform Environment...${NC}"

# 1. Check if .env exists
echo -e "\n${YELLOW}--- [1/3] Checking Config ---${NC}"
if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
    echo -e "${YELLOW}⚠️  Config file not found. Creating from .env.example...${NC}"
    cp "$PROJECT_ROOT/backend/.env.example" "$PROJECT_ROOT/backend/.env"
    echo -e "${RED}❗ Please edit backend/.env with your API keys.${NC}"
else
    echo -e "${GREEN}✅ Config file exists.${NC}"
fi

# 2. Run dependency installation
echo -e "\n${YELLOW}--- [2/3] Installing Dependencies ---${NC}"
bash "$PROJECT_ROOT/install_deps.sh"

# 3. Create initial data directories if needed
echo -e "\n${YELLOW}--- [3/3] Setting Up Data Directories ---${NC}"
mkdir -p "$PROJECT_ROOT/data/uploads"
echo -e "${GREEN}✅ Data directories ready.${NC}"

echo -e "\n------------------------------------"
echo -e "${GREEN}✨ Setup completed!${NC}"
echo -e "💡 Run ${YELLOW}./start.sh${NC} to start the platform."
