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
    echo "Using uv for backend dependency management..."
    cd backend
    uv sync
    echo "Backend dependencies synced successfully with uv."
    cd "$PROJECT_ROOT"
elif [ -d "backend/venv" ]; then
    echo "Backend virtual environment already exists. Updating dependencies..."
    source backend/venv/bin/activate
    pip install --upgrade pip
    if [ -f "backend/requirements.txt" ]; then
        pip install -r backend/requirements.txt
        echo "Backend dependencies updated successfully."
    fi
    deactivate
else
    echo "Backend virtual environment not found. Creating and installing dependencies..."
    if [ -d "backend" ]; then
        cd backend
        if command -v python3 &> /dev/null; then
            python3 -m venv venv
            source venv/bin/activate
            pip install --upgrade pip
            if [ -f "requirements.txt" ]; then
                pip install -r requirements.txt
                echo "Backend dependencies installed successfully."
            else
                echo "Warning: requirements.txt not found in backend directory."
            fi
            deactivate
        else
            echo "Error: python3 is not installed. Please install Python 3."
            exit 1
        fi
        cd "$PROJECT_ROOT"
    else
        echo "Warning: backend directory not found."
    fi
fi

echo "--- Done ---"
echo "All dependencies checked/installed."
