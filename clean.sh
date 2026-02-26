#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}🧹 Starting Deep Cleanup...${NC}"

# 1. Clean Backend
echo -e "\n${YELLOW}--- [1/2] Cleaning Backend ---${NC}"
cd "$PROJECT_ROOT/backend"
echo "Removing backend artifacts..."
rm -rf venv/
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -rf .coverage
rm -rf .mypy_cache/
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
echo -e "${GREEN}✅ Backend cleanup finished.${NC}"

# 2. Clean Frontend
echo -e "\n${YELLOW}--- [2/2] Cleaning Frontend ---${NC}"
cd "$PROJECT_ROOT/frontend"
echo "Removing frontend artifacts..."
rm -rf node_modules/
rm -rf dist/
rm -rf .vitest_cache/
rm -rf .playwright/
rm -rf playwright-report/
rm -rf test-results/
echo -e "${GREEN}✅ Frontend cleanup finished.${NC}"

# 3. Root Level
echo -e "\n${YELLOW}--- Root Artifacts ---${NC}"
cd "$PROJECT_ROOT"
rm -f backend.log frontend.log
echo "Removing logs..."

echo -e "\n------------------------------------"
echo -e "${GREEN}✨ Project is clean! You can now run ./install_deps.sh to reinstall.${NC}"
