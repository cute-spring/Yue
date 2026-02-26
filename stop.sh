#!/bin/bash

echo "🛑 Stopping Yue Agent Platform services..."

stop_by_pattern() {
    local label="$1"
    local pattern="$2"
    local pids
    pids=$(pgrep -f "$pattern" || true)
    if [ -n "$pids" ]; then
        echo "Stopping $label processes (PIDs: $pids)..."
        kill $pids 2>/dev/null || true
        for pid in $pids; do
            for _ in {1..10}; do
                if ps -p "$pid" > /dev/null 2>&1; then
                    sleep 0.5
                else
                    break
                fi
            done
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
    else
        echo "No $label process found."
    fi
}

stop_by_pattern "backend" "python -m app.main"
stop_by_pattern "frontend" "vite"

echo "✅ Services stopped."
