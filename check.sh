#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=0
MODE="${1:-full}"

echo -e "${GREEN}🔍 Starting Full Stack Quality Check...${NC}"

fail_and_exit() {
    echo -e "\n------------------------------------"
    echo -e "${RED}🚩 Some checks failed. Please review the logs above.${NC}"
    exit 1
}

run_env_precheck() {
    cd "$PROJECT_ROOT/backend"
    if [ ! -d ".venv" ]; then
        echo -e "${RED}⚠️  Backend .venv not found. Skipping env precheck.${NC}"
        echo "ENV_PRECHECK:FAIL:NO_VENV"
        return 1
    fi
    source .venv/bin/activate
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    if python3 -m pytest tests/test_00_env_precheck.py -q -rs; then
        echo -e "${GREEN}✅ Backend env precheck completed.${NC}"
        echo "ENV_PRECHECK:OK"
        deactivate
        return 0
    fi
    echo -e "${RED}❌ Backend env precheck failed.${NC}"
    echo "ENV_PRECHECK:FAIL"
    deactivate
    return 1
}

if [ "$MODE" = "--env-precheck" ]; then
    run_env_precheck
    exit $?
fi

echo -e "\n${YELLOW}--- [1/4] Backend: ENV_PRECHECK ---${NC}"
if ! run_env_precheck; then
    fail_and_exit
fi

# 2. Backend Checks
echo -e "\n${YELLOW}--- [2/4] Backend: Pytest (Unit Tests) ---${NC}"
cd "$PROJECT_ROOT/backend"
if [ -d ".venv" ]; then
    source .venv/bin/activate
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    # 仅运行单元测试，跳过需要运行中服务的集成测试
    if python3 -m pytest -m "not integration"; then
        echo -e "${GREEN}✅ Backend unit tests passed.${NC}"
    else
        echo -e "${RED}❌ Backend unit tests failed.${NC}"
        deactivate
        fail_and_exit
    fi
    deactivate
else
    echo -e "${RED}⚠️  Backend .venv not found. Skipping backend tests.${NC}"
    fail_and_exit
fi

# 3. Frontend: Type Check
echo -e "\n${YELLOW}--- [3/4] Frontend: TypeScript Check ---${NC}"
cd "$PROJECT_ROOT/frontend"
if [ -d "node_modules" ]; then
    if npm run build -- --noEmit 2>/dev/null || npx tsc --noEmit; then
        echo -e "${GREEN}✅ Frontend type check passed.${NC}"
    else
        echo -e "${RED}❌ Frontend type check failed.${NC}"
        fail_and_exit
    fi
else
    echo -e "${RED}⚠️  Frontend node_modules not found. Skipping type check.${NC}"
    fail_and_exit
fi

# 4. Frontend: Unit Tests
echo -e "\n${YELLOW}--- [4/4] Frontend: Vitest ---${NC}"
if [ -d "node_modules" ]; then
    if npm run test; then
        echo -e "${GREEN}✅ Frontend unit tests passed.${NC}"
    else
        echo -e "${RED}❌ Frontend unit tests failed.${NC}"
        fail_and_exit
    fi
else
    echo -e "${RED}⚠️  Frontend node_modules not found. Skipping frontend tests.${NC}"
    fail_and_exit
fi

echo -e "\n------------------------------------"
echo -e "${GREEN}✨ All checks passed! Ready to commit.${NC}"
exit 0
