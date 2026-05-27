#!/bin/bash

set -e
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HEALTH_URL="http://127.0.0.1:8003/api/health"
BACKEND_MAX_WAIT_SECONDS=60
FRONTEND_URL="http://localhost:3000"
FRONTEND_MAX_WAIT_SECONDS=60
YUE_SKILL_RUNTIME_MODE="${YUE_SKILL_RUNTIME_MODE:-legacy}"
BACKEND_PYTHON=""

log() {
    echo "$1"
}

add_path_if_dir() {
    local dir="$1"
    if [ -d "$dir" ] && [[ ":$PATH:" != *":$dir:"* ]]; then
        PATH="$dir:$PATH"
    fi
}

ensure_runtime_tooling() {
    add_path_if_dir "/Applications/Codex.app/Contents/Resources"
    add_path_if_dir "/opt/homebrew/bin"
    add_path_if_dir "/usr/local/bin"
}

resolve_backend_python() {
    if [ -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
        BACKEND_PYTHON="$ROOT_DIR/backend/.venv/bin/python"
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        BACKEND_PYTHON="$(command -v python)"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        BACKEND_PYTHON="$(command -v python3)"
        return 0
    fi
    return 1
}

require_frontend_runtime() {
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        return 0
    fi

    log "❌ Node.js/npm were not found on PATH."
    log "   Checked PATH: $PATH"
    log "   Install Node.js or update start.sh PATH bootstrap locations."
    exit 1
}

frontend_healthcheck() {
    (
        cd "$ROOT_DIR/frontend"
        node -e "require('rollup'); console.log('rollup-ok')" >/dev/null 2>&1
    )
}

activate_rollup_wasm_fallback() {
    (
        cd "$ROOT_DIR/frontend"

        if [ ! -d "node_modules/@rollup/wasm-node" ]; then
            echo "ℹ️  Installing @rollup/wasm-node fallback..."
            npm install
        fi

        if [ -e "node_modules/rollup" ] || [ -L "node_modules/rollup" ]; then
            rm -rf "node_modules/rollup"
        fi

        ln -sfn "@rollup/wasm-node" "node_modules/rollup"
    )
}

repair_frontend_deps() {
    log "🛠️  Repairing frontend dependencies..."
    (
        cd "$ROOT_DIR/frontend"

        if [ ! -f "package.json" ]; then
            echo "❌ frontend/package.json not found."
            exit 1
        fi

        if [ ! -d "node_modules" ]; then
            echo "ℹ️  node_modules not found. Running npm install..."
            npm install
            return
        fi

        echo "ℹ️  Attempting targeted Rollup repair..."
        rm -rf node_modules/@rollup
        npm install

        if node -e "require('rollup')" >/dev/null 2>&1; then
            echo "✅ Targeted Rollup repair succeeded."
            return
        fi

        echo "ℹ️  Native Rollup is still unavailable. Switching to the WASM Rollup fallback..."
        npm install
        if [ -e "node_modules/rollup" ] || [ -L "node_modules/rollup" ]; then
            rm -rf "node_modules/rollup"
        fi
        ln -sfn "@rollup/wasm-node" "node_modules/rollup"

        if node -e "require('rollup')" >/dev/null 2>&1; then
            echo "✅ WASM Rollup fallback activated successfully."
            return
        fi

        echo "ℹ️  WASM fallback did not recover frontend runtime. Reinstalling frontend dependencies..."
        rm -rf node_modules
        npm install
        if [ -e "node_modules/rollup" ] || [ -L "node_modules/rollup" ]; then
            rm -rf "node_modules/rollup"
        fi
        ln -sfn "@rollup/wasm-node" "node_modules/rollup"
    )
}

ensure_frontend_runtime_ready() {
    if frontend_healthcheck; then
        log "✅ Frontend runtime dependencies look healthy."
        return
    fi

    log "⚠️  Frontend runtime dependency check failed."
    repair_frontend_deps

    if frontend_healthcheck; then
        log "✅ Frontend runtime dependencies repaired successfully."
        return
    fi

    log "❌ Frontend dependency repair failed. Please inspect frontend dependencies manually."
    exit 1
}

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

ensure_runtime_tooling

echo "🚀 Starting Yue Agent Platform..."
echo "🧠 Skill runtime mode: ${YUE_SKILL_RUNTIME_MODE}"

echo "📡 Starting backend service on http://127.0.0.1:8003..."
cd "$ROOT_DIR/backend"

if ! resolve_backend_python; then
    echo "❌ No usable Python interpreter was found."
    echo "   Expected backend/.venv/bin/python, python, or python3."
    exit 1
fi

if ! "$BACKEND_PYTHON" - <<'PY' >/dev/null 2>&1
try:
    import midterm_memory  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
then
    if [ -d "$ROOT_DIR/../midterm-session-memory/src" ]; then
        echo "⚠️  midterm-session-memory is not installed; falling back to sibling src/ on PYTHONPATH."
        export PYTHONPATH="$ROOT_DIR/../midterm-session-memory/src:${PYTHONPATH:-}"
    else
        echo "❌ midterm-session-memory is not installed and no sibling source checkout was found."
        echo "   Run ./setup.sh first, or install the package manually."
        exit 1
    fi
fi

YUE_SKILL_RUNTIME_MODE="$YUE_SKILL_RUNTIME_MODE" "$BACKEND_PYTHON" -m app.main > "$ROOT_DIR/backend.log" 2>&1 &
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
require_frontend_runtime
ensure_frontend_runtime_ready
cd "$ROOT_DIR/frontend"
npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo -n "⏳ Waiting for frontend to become reachable"
WAIT_ELAPSED=0
until curl -sSf "$FRONTEND_URL" > /dev/null 2>&1; do
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo ""
        echo "❌ Frontend process exited unexpectedly."
        echo "📝 Check frontend.log for details."
        exit 1
    fi
    if [ "$WAIT_ELAPSED" -ge "$FRONTEND_MAX_WAIT_SECONDS" ]; then
        echo ""
        echo "❌ Frontend did not become reachable within ${FRONTEND_MAX_WAIT_SECONDS}s."
        echo "📝 Check frontend.log for details."
        exit 1
    fi
    echo -n "."
    sleep 1
    WAIT_ELAPSED=$((WAIT_ELAPSED + 1))
done
echo " ready"

echo "✅ Both services are running."
echo "📝 Logs are being written to backend.log and frontend.log"
echo "🛑 Press Ctrl+C to stop both services."

wait $BACKEND_PID $FRONTEND_PID
