#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YUE_SKILL_RUNTIME_MODE="${YUE_SKILL_RUNTIME_MODE:-legacy}"
YUE_BACKEND_HOST="${YUE_BACKEND_HOST:-0.0.0.0}"
YUE_BACKEND_PORT="${YUE_BACKEND_PORT:-8003}"
YUE_FRONTEND_HOST="${YUE_FRONTEND_HOST:-0.0.0.0}"
YUE_FRONTEND_PORT="${YUE_FRONTEND_PORT:-3000}"

detect_lan_ip() {
    local ip=""
    for iface in en0 en1; do
        ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
        if [ -n "$ip" ]; then
            echo "$ip"
            return 0
        fi
    done

    echo "127.0.0.1"
}

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping dev servers...${NC}"
    # Kill background jobs
    jobs -p | xargs kill 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}🚀 Starting Yue Agent Platform in Dev Mode...${NC}"
echo -e "${GREEN}🧠 Skill runtime mode: ${YUE_SKILL_RUNTIME_MODE}${NC}"
LAN_IP="$(detect_lan_ip)"

# 1. Start Backend
echo -e "${YELLOW}📡 Starting backend (bound to ${YUE_BACKEND_HOST}:${YUE_BACKEND_PORT})...${NC}"
cd "$PROJECT_ROOT/backend"
if command -v uv &> /dev/null; then
    YUE_BACKEND_HOST="$YUE_BACKEND_HOST" YUE_BACKEND_PORT="$YUE_BACKEND_PORT" YUE_SKILL_RUNTIME_MODE="$YUE_SKILL_RUNTIME_MODE" uv run python -m app.main &
    BACKEND_PID=$!
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    YUE_BACKEND_HOST="$YUE_BACKEND_HOST" YUE_BACKEND_PORT="$YUE_BACKEND_PORT" YUE_SKILL_RUNTIME_MODE="$YUE_SKILL_RUNTIME_MODE" python -m app.main &
    BACKEND_PID=$!
else
    echo -e "${RED}⚠️  Backend environment not found. Run ./setup.sh first.${NC}"
    exit 1
fi

# 2. Start Frontend
echo -e "${YELLOW}💻 Starting frontend (bound to ${YUE_FRONTEND_HOST}:${YUE_FRONTEND_PORT})...${NC}"
cd "$PROJECT_ROOT/frontend"
if [ -d "node_modules" ]; then
    YUE_FRONTEND_HOST="$YUE_FRONTEND_HOST" YUE_FRONTEND_PORT="$YUE_FRONTEND_PORT" npm run dev &
    FRONTEND_PID=$!
else
    echo -e "${RED}⚠️  Frontend node_modules not found. Run ./setup.sh first.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Both services are running.${NC}"
echo -e "💡 Local frontend: http://localhost:${YUE_FRONTEND_PORT}"
echo -e "💡 LAN frontend:   http://${LAN_IP}:${YUE_FRONTEND_PORT}"
echo -e "💡 LAN backend:     http://${LAN_IP}:${YUE_BACKEND_PORT}"
echo -e "🛑 Press Ctrl+C to stop both servers."

# Wait for background processes to finish
wait $BACKEND_PID $FRONTEND_PID
