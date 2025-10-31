#!/bin/bash

# Source2Target Development Script

echo "🚀 Starting Source2Target Development Environment"
echo ""

# Check if we're in the right directory
if [ ! -f "app.yaml" ]; then
    echo "❌ Error: Must run this script from the project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Node.js
if ! command_exists node; then
    echo "❌ Error: Node.js is not installed"
    exit 1
fi

# Check Python
if ! command_exists python3; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    echo "✅ Frontend dependencies installed"
else
    echo "✅ Frontend dependencies already installed"
fi

# Install backend dependencies if needed
echo "📦 Checking Python dependencies..."
pip3 install -q -r requirements.txt
echo "✅ Backend dependencies ready"
echo ""

echo "🎯 Starting Development Servers..."
echo ""
echo "Frontend will be available at: http://localhost:5173"
echo "Backend will be available at: http://localhost:8000"
echo "Backend API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Start backend in background
cd backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend in background
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID

