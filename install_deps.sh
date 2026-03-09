#!/bin/bash

# Exit on error
set -e

PROJECT_ROOT=$(pwd)

echo "Checking dependencies..."

# Frontend detection and installation
echo "--- Frontend ---"
if [ -d "frontend/node_modules" ]; then
    echo "Frontend dependencies already installed. Skipping."
else
    echo "Frontend dependencies not found. Installing..."
    if [ -d "frontend" ]; then
        cd frontend
        if command -v npm &> /dev/null; then
            npm install
            echo "Frontend dependencies installed successfully."
        else
            echo "Error: npm is not installed. Please install Node.js and npm."
            exit 1
        fi
        cd "$PROJECT_ROOT"
    else
        echo "Warning: frontend directory not found."
    fi
fi

# Backend detection and installation
echo "--- Backend ---"

if command -v uv &> /dev/null; then
    echo "uv detected. Using uv for backend dependency management..."
    cd backend
    uv sync
    echo "Backend dependencies synced successfully with uv."
    cd "$PROJECT_ROOT"
else
    echo "uv not found. Falling back to pip..."
    
    if [ ! -d "backend" ]; then
        echo "Error: backend directory not found."
        exit 1
    fi

    cd backend
    
    # Check for python3
    if ! command -v python3 &> /dev/null; then
        echo "Error: python3 is not installed. Please install Python 3."
        exit 1
    fi

    # Create venv if not exists
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi

    # Activate venv
    source .venv/bin/activate
    
    echo "Upgrading pip..."
    pip install --upgrade pip

    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
        echo "Backend dependencies installed successfully with pip."
    else
        echo "Warning: requirements.txt not found. Skipping dependency installation."
    fi
    
    deactivate
    cd "$PROJECT_ROOT"
fi

echo "--- Done ---"
echo "All dependencies checked/installed."
