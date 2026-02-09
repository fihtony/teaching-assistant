#!/bin/bash

# ===============================================
# English Teaching Assignment Grading System
# Start Script for macOS/Linux
# ===============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  English Teaching Assignment Grading System${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check Python version
check_python() {
    echo -e "${YELLOW}Checking Python installation...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}✗ Python 3 is not installed. Please install Python 3.9+${NC}"
        exit 1
    fi
}

# Check Node.js version
check_node() {
    echo -e "${YELLOW}Checking Node.js installation...${NC}"
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
    else
        echo -e "${RED}✗ Node.js is not installed. Please install Node.js 18+${NC}"
        exit 1
    fi
}

# Setup Python virtual environment and install dependencies
setup_backend() {
    echo ""
    echo -e "${YELLOW}Setting up backend...${NC}"
    
    cd "$PROJECT_ROOT/backend"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -r requirements.txt > /dev/null 2>&1
    
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
    
    # Create required directories
    mkdir -p data logs
    mkdir -p ../uploads ../graded ../templates ../cache
    
    echo -e "${GREEN}✓ Directory structure created${NC}"
}

# Setup frontend and install dependencies
setup_frontend() {
    echo ""
    echo -e "${YELLOW}Setting up frontend...${NC}"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Install dependencies
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install > /dev/null 2>&1
    fi
    
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
}

# Start backend server
start_backend() {
    echo ""
    echo -e "${YELLOW}Starting backend server...${NC}"
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    # Ensure logs directory exists
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Check if port 8090 is in use
    if lsof -Pi :8090 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port 8090 is in use. Stopping existing process...${NC}"
        kill $(lsof -t -i:8090) 2>/dev/null || true
        sleep 2
    fi
    
    # Start backend in background with proper logging
    # Use bash subshell to ensure environment variables are properly inherited
    (python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload >> "$PROJECT_ROOT/logs/backend.log" 2>&1) &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$PROJECT_ROOT/.backend.pid"
    
    # Wait for backend to start
    sleep 4
    
    # Check if process is still running
    if kill -0 $BACKEND_PID 2>/dev/null; then
        if curl -s http://localhost:8090/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend started on http://localhost:8090${NC}"
        else
            echo -e "${YELLOW}Backend started (PID: $BACKEND_PID) - waiting for readiness...${NC}"
            sleep 2
        fi
    else
        echo -e "${RED}✗ Backend failed to start. Check logs/backend.log${NC}"
        cat "$PROJECT_ROOT/logs/backend.log" | tail -20
        return 1
    fi
}

# Start frontend server
start_frontend() {
    echo ""
    echo -e "${YELLOW}Starting frontend server...${NC}"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Ensure logs directory exists
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Check if port 3090 is in use
    if lsof -Pi :3090 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port 3090 is in use. Stopping existing process...${NC}"
        kill $(lsof -t -i:3090) 2>/dev/null || true
        sleep 2
    fi
    
    # Start frontend in background with proper logging
    (npm run dev >> "$PROJECT_ROOT/logs/frontend.log" 2>&1) &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PROJECT_ROOT/.frontend.pid"
    
    sleep 5
    
    # Check if process is still running
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        if curl -s http://localhost:3090 > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Frontend started on http://localhost:3090${NC}"
        else
            echo -e "${YELLOW}Frontend started (PID: $FRONTEND_PID) - waiting for readiness...${NC}"
            sleep 3
        fi
    else
        echo -e "${RED}✗ Frontend failed to start. Check logs/frontend.log${NC}"
        cat "$PROJECT_ROOT/logs/frontend.log" 2>/dev/null | tail -20 || echo "No log file yet"
        return 1
    fi
}

# Main execution
main() {
    check_python
    check_node
    setup_backend
    setup_frontend
    start_backend
    start_frontend
    
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  System started successfully!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo -e "  ${BLUE}Frontend:${NC} http://localhost:3090"
    echo -e "  ${BLUE}Backend API:${NC} http://localhost:8090"
    echo -e "  ${BLUE}API Docs:${NC} http://localhost:8090/docs"
    echo ""
    echo -e "  To stop the system, run: ${YELLOW}./scripts/stop.sh${NC}"
    echo ""
}

main
