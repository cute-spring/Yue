#!/bin/bash

set -e
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HEALTH_URL="http://127.0.0.1:8003/api/health"
BACKEND_MAX_WAIT_SECONDS=60

cleanup() {
    echo ""
    echo "Stopping services..."
    if [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
    exit
}

trap cleanup SIGINT SIGTERM

echo "🚀 Starting Yue Agent Platform..."

echo "📡 Starting backend service on http://127.0.0.1:8003..."
cd "$ROOT_DIR/backend"
if command -v uv &> /dev/null; then
    uv run python -m app.main > "$ROOT_DIR/backend.log" 2>&1 &
elif [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
    python -m app.main > "$ROOT_DIR/backend.log" 2>&1 &
else
    echo "⚠️  Warning: backend environment not found. Attempting to run with system python..."
    python -m app.main > "$ROOT_DIR/backend.log" 2>&1 &
fi
BACKEND_PID=$!
cd "$ROOT_DIR"

echo -n "⏳ Waiting for backend to become reachable"
WAIT_ELAPSED=0
until curl -sSf "$BACKEND_HEALTH_URL" > /dev/null 2>&1; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "❌ Backend process exited unexpectedly. Check backend.log"
        exit 1
    fi
    if [ "$WAIT_ELAPSED" -ge "$BACKEND_MAX_WAIT_SECONDS" ]; then
        echo ""
        echo "❌ Backend did not become reachable within ${BACKEND_MAX_WAIT_SECONDS}s. Check backend.log"
        exit 1
    fi
    echo -n "."
    sleep 1
    WAIT_ELAPSED=$((WAIT_ELAPSED + 1))
done
echo " ready"

echo "💻 Starting frontend service on http://localhost:3000..."
cd "$ROOT_DIR/frontend"
npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo "✅ Both services are starting in the background."
echo "📝 Logs are being written to backend.log and frontend.log"
echo "🛑 Press Ctrl+C to stop both services."

wait $BACKEND_PID $FRONTEND_PID
