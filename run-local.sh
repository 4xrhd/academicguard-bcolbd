#!/bin/bash

# run-local.sh — AcademicGuard local dev runtime launcher
# Starts podman/docker containers, activates the Python venv, and runs the stack in one command.

# 1. Determine script directory to support execution from any path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_PATH="$BACKEND_DIR/venv/bin/activate"

echo "========================================================"
echo "             ACADEMICGUARD LOCAL RUNTIME                "
echo "========================================================"

# 2. Activate Python virtual environment (venv)
if [ -f "$VENV_PATH" ]; then
    echo "⚡ Activating Python virtual environment..."
    source "$VENV_PATH"
else
    echo "❌ Error: Python virtual environment not found at $VENV_PATH"
    echo "Please make sure the backend/venv directory exists and is set up."
    (return 0 2>/dev/null) && return || exit 1
fi

# 3. Detect container engine (podman or docker) and start DB/Redis services
if command -v podman &> /dev/null; then
    CONTAINER_ENGINE="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_ENGINE="docker"
else
    echo "⚠️ Warning: Neither 'podman' nor 'docker' commands found in PATH."
    echo "Skipping container databases startup. Ensure PostgreSQL and Redis are running locally."
    CONTAINER_ENGINE=""
fi

if [ -n "$CONTAINER_ENGINE" ]; then
    echo "🐳 Using container engine: $CONTAINER_ENGINE"
    
    # Check if ag-db container exists, if not, create it
    if ! $CONTAINER_ENGINE inspect ag-db &>/dev/null; then
        echo "   Creating postgres container (ag-db)..."
        $CONTAINER_ENGINE run -d --name ag-db \
          -e POSTGRES_DB=academicguard \
          -e POSTGRES_USER=academicguard \
          -e POSTGRES_PASSWORD=b53fcee4e923d5b51109fc46 \
          -p 5432:5432 \
          -v ag-db-data:/var/lib/postgresql/data \
          postgres:15-alpine
    else
        echo "   Starting postgres container (ag-db)..."
        $CONTAINER_ENGINE start ag-db
    fi

    # Check if ag-redis container exists, if not, create it
    if ! $CONTAINER_ENGINE inspect ag-redis &>/dev/null; then
        echo "   Creating redis container (ag-redis)..."
        $CONTAINER_ENGINE run -d --name ag-redis \
          -p 6379:6379 \
          -v ag-redis-data:/data \
          redis:7-alpine
    else
        echo "   Starting redis container (ag-redis)..."
        $CONTAINER_ENGINE start ag-redis
    fi
    
    echo "⌛ Waiting 3 seconds for databases to initialize..."
    sleep 3
fi

# 4. Define exit / cleanup routine to gracefully shut down background tasks
cleanup() {
    echo ""
    echo "🛑 Stopping FastAPI backend and static web servers..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    echo "Services stopped. Exiting."
    (return 0 2>/dev/null) && return || exit 0
}

trap cleanup INT TERM

# 5. Start backend (FastAPI) in the background
echo "🚀 Starting backend API (FastAPI) on port 8000..."
cd "$BACKEND_DIR"
export PYTHONPATH="$BACKEND_DIR"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# 6. Start frontend (Static Server) in the background
echo "🚀 Starting frontend server (Python http.server) on port 8080..."
python -m http.server 8080 --directory "$FRONTEND_DIR" &
FRONTEND_PID=$!

echo "--------------------------------------------------------"
echo "🎉 AcademicGuard development stack is fully active!"
echo "   - Frontend UI: http://localhost:8080"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs:    http://localhost:8000/api/docs"
echo "--------------------------------------------------------"
echo "👉 Press Ctrl+C to terminate both servers and clean up."
echo "--------------------------------------------------------"

# Wait for both background processes to keep shell open
wait $BACKEND_PID $FRONTEND_PID
