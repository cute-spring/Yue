#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping dev servers...${NC}"
    # Kill background jobs
    jobs -p | xargs kill 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}🚀 Starting Yue Agent Platform in Dev Mode...${NC}"

# 1. Start Backend
echo -e "${YELLOW}📡 Starting backend...${NC}"
cd "$PROJECT_ROOT/backend"
if [ -d "venv" ]; then
    source venv/bin/activate
    python -m app.main &
    BACKEND_PID=$!
else
    echo -e "${RED}⚠️  Backend venv not found. Run ./setup.sh first.${NC}"
    exit 1
fi

# 2. Start Frontend
echo -e "${YELLOW}💻 Starting frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
if [ -d "node_modules" ]; then
    npm run dev &
    FRONTEND_PID=$!
else
    echo -e "${RED}⚠️  Frontend node_modules not found. Run ./setup.sh first.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Both services are running.${NC}"
echo -e "💡 Backend: http://127.0.0.1:8000"
echo -e "💡 Frontend: http://localhost:3000"
echo -e "🛑 Press Ctrl+C to stop both servers."

# Wait for background processes to finish
wait $BACKEND_PID $FRONTEND_PID
