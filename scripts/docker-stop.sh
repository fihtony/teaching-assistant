#!/bin/bash

# ===============================================
# Docker Compose Stop Script
# Stops backend and frontend services
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
echo -e "${BLUE}  Docker Compose Stop Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if services are running
echo -e "${YELLOW}⏸️  Stopping services...${NC}"
docker-compose -f "$PROJECT_ROOT/docker-compose.yml" down

echo -e "${GREEN}✅ Services stopped${NC}"
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Cleanup completed!${NC}"
echo -e "${GREEN}   Your data is preserved:${NC}"
echo -e "${GREEN}   ✓ ~/apps/teaching-assistant/data${NC}"
echo -e "${GREEN}   ✓ ~/apps/teaching-assistant/logs${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
