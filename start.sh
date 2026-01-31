#!/bin/bash

# Function to handle script termination
cleanup() {
    echo ""
    echo "Stopping services..."
    # Kill the process groups to ensure all children are stopped
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "🚀 Starting Yue Agent Platform..."

# 1. Start Backend
echo "📡 Starting backend service on http://127.0.0.1:8000..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  Warning: backend/venv not found. Attempting to run with system python..."
fi
python -m app.main > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# 2. Start Frontend
echo "💻 Starting frontend service on http://localhost:3000..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "✅ Both services are starting in the background."
echo "📝 Logs are being written to backend.log and frontend.log"
echo "🛑 Press Ctrl+C to stop both services."

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID
