#!/bin/bash

set -u

PROJECT_ROOT=$(pwd)
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv"
MAX_RETRIES=3
BASE_DELAY=2
FAILED=0

echo "Checking dependencies..."

run_with_retry() {
    local label="$1"
    shift
    local attempt=1
    local delay=$BASE_DELAY
    while true; do
        "$@" && return 0
        if [ $attempt -ge $MAX_RETRIES ]; then
            echo "$label failed after $MAX_RETRIES attempts."
            return 1
        fi
        echo "$label failed. Retrying in ${delay}s..."
        sleep $delay
        attempt=$((attempt + 1))
        delay=$((delay * 2))
    done
}

echo "--- Frontend ---"
if [ -d "$FRONTEND_DIR" ]; then
    if [ -d "$FRONTEND_DIR/node_modules" ]; then
        echo "Frontend dependencies already installed. Skipping."
    else
        if command -v npm &> /dev/null; then
            cd "$FRONTEND_DIR"
            run_with_retry "npm install" npm install || {
                echo "npm install failed. Trying cache clean and retry..."
                npm cache clean --force || true
                run_with_retry "npm install (after cache clean)" npm install || FAILED=1
            }
            if [ $FAILED -eq 0 ]; then
                echo "Frontend dependencies installed successfully."
            fi
            cd "$PROJECT_ROOT"
        else
            echo "Error: npm is not installed. Please install Node.js and npm."
            FAILED=1
        fi
    fi
else
    echo "Warning: frontend directory not found."
fi

echo "--- Backend ---"
if [ -d "$BACKEND_DIR" ]; then
    if [ -d "$VENV_DIR" ]; then
        echo "Backend virtual environment already exists. Skipping."
    else
        if command -v python3 &> /dev/null; then
            cd "$BACKEND_DIR"
            run_with_retry "python3 -m venv .venv" python3 -m venv .venv || FAILED=1
            if [ -d "$VENV_DIR" ]; then
                source "$VENV_DIR/bin/activate"
                run_with_retry "pip install --upgrade pip" pip install --upgrade pip || FAILED=1
                if [ -f "requirements.txt" ]; then
                    run_with_retry "pip install -r requirements.txt" pip install -r requirements.txt || {
                        echo "pip install failed. Trying no-cache and retry..."
                        run_with_retry "pip install -r requirements.txt (no-cache)" pip install --no-cache-dir -r requirements.txt || FAILED=1
                    }
                    if [ $FAILED -eq 0 ]; then
                        echo "Backend dependencies installed successfully."
                    fi
                else
                    echo "Warning: requirements.txt not found in backend directory."
                    FAILED=1
                fi
                deactivate
            else
                FAILED=1
            fi
            cd "$PROJECT_ROOT"
        else
            echo "Error: python3 is not installed. Please install Python 3."
            FAILED=1
        fi
    fi
else
    echo "Warning: backend directory not found."
fi

echo "--- Done ---"
if [ $FAILED -eq 0 ]; then
    echo "All dependencies checked/installed."
    exit 0
else
    echo "Some dependencies failed to install."
    exit 1
fi
