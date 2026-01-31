#!/bin/bash

echo "🛑 Stopping Yue Agent Platform services..."

# 1. Stop Backend (FastAPI / Uvicorn)
BACKEND_PIDS=$(pgrep -f "python -m app.main")
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "Stopping backend processes (PIDs: $BACKEND_PIDS)..."
    kill $BACKEND_PIDS
else
    echo "No backend process found."
fi

# 2. Stop Frontend (Vite)
FRONTEND_PIDS=$(pgrep -f "vite")
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "Stopping frontend processes (PIDs: $FRONTEND_PIDS)..."
    kill $FRONTEND_PIDS
else
    echo "No frontend process found."
fi

echo "✅ Services stopped."
