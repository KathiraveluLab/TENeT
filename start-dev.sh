#!/bin/bash

# TENeT Development Server Startup Script
# Starts both backend and frontend in separate terminal tabs/windows

echo "🚀 Starting TENeT Development Servers..."

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Detected macOS - Opening servers in new Terminal tabs..."
    
    # Backend
    osascript -e 'tell application "Terminal"
        do script "cd \"'$(pwd)'/backend\" && echo \"🔧 Starting Backend Server...\" && source venv/bin/activate && uvicorn app.main:app --reload --port 8000"
    end tell'
    
    # Frontend
    osascript -e 'tell application "Terminal"
        do script "cd \"'$(pwd)'/frontend\" && echo \"🎨 Starting Frontend Server...\" && npm run dev"
    end tell'
    
    echo "✅ Servers launched in separate Terminal tabs"
    echo ""
    echo "📍 Backend:  http://localhost:8000"
    echo "📍 API Docs: http://localhost:8000/api/docs"
    echo "📍 Frontend: http://localhost:5173"
    
else
    # For Linux or other systems, start in background
    echo "🐧 Starting servers in background..."
    
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --reload --port 8000 &
    BACKEND_PID=$!
    
    cd ../frontend
    npm run dev &
    FRONTEND_PID=$!
    
    echo "✅ Servers started"
    echo ""
    echo "📍 Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
    echo "📍 API Docs: http://localhost:8000/api/docs"
    echo "📍 Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
    echo ""
    echo "To stop servers:"
    echo "  kill $BACKEND_PID $FRONTEND_PID"
fi

echo ""
echo "💡 Wait a few seconds for servers to start, then open:"
echo "   http://localhost:5173"
