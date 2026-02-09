#!/bin/bash

# ===============================================
# English Teaching Assignment Grading System
# Stop Script for macOS/Linux
# ===============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Stopping Assignment Grading System${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Stop backend
stop_backend() {
    echo -e "${YELLOW}Stopping backend server...${NC}"
    
    if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
        BACKEND_PID=$(cat "$PROJECT_ROOT/.backend.pid")
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID 2>/dev/null
            echo -e "${GREEN}✓ Backend stopped (PID: $BACKEND_PID)${NC}"
        else
            echo -e "${YELLOW}Backend process not running${NC}"
        fi
        rm -f "$PROJECT_ROOT/.backend.pid"
    else
        # Try to kill by port
        if lsof -Pi :8090 -sTCP:LISTEN -t >/dev/null 2>&1; then
            kill $(lsof -t -i:8090) 2>/dev/null
            echo -e "${GREEN}✓ Backend stopped${NC}"
        else
            echo -e "${YELLOW}No backend process found${NC}"
        fi
    fi
}

# Stop frontend
stop_frontend() {
    echo -e "${YELLOW}Stopping frontend server...${NC}"
    
    if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend.pid")
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID 2>/dev/null
            echo -e "${GREEN}✓ Frontend stopped (PID: $FRONTEND_PID)${NC}"
        else
            echo -e "${YELLOW}Frontend process not running${NC}"
        fi
        rm -f "$PROJECT_ROOT/.frontend.pid"
    else
        # Try to kill by port
        if lsof -Pi :3090 -sTCP:LISTEN -t >/dev/null 2>&1; then
            kill $(lsof -t -i:3090) 2>/dev/null
            echo -e "${GREEN}✓ Frontend stopped${NC}"
        else
            echo -e "${YELLOW}No frontend process found${NC}"
        fi
    fi
}

# Main execution
main() {
    stop_backend
    stop_frontend
    
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  System stopped successfully!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
}

main
