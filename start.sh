#!/bin/bash

set -e
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo "📡 Starting backend service on http://127.0.0.1:8000..."
cd "$ROOT_DIR/backend"
if [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
else
    echo "⚠️  Warning: backend/venv not found. Attempting to run with system python..."
fi
python -m app.main > "$ROOT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
cd "$ROOT_DIR"

echo "💻 Starting frontend service on http://localhost:3000..."
cd "$ROOT_DIR/frontend"
npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo "✅ Both services are starting in the background."
echo "📝 Logs are being written to backend.log and frontend.log"
echo "🛑 Press Ctrl+C to stop both services."

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID
