#!/bin/bash

# ===============================================
# Docker Compose Start Script
# Syncs versions from .version.json, stops if running, and restarts
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
echo -e "${BLUE}  Docker Compose Start Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Sync versions from .version.json to .env
echo -e "${YELLOW}📝 Syncing versions from .version.json...${NC}"

VERSION_FILE="$PROJECT_ROOT/.version.json"
ENV_FILE="$PROJECT_ROOT/.env"

# Read versions from .version.json
BACKEND_VERSION="0.1.0"
FRONTEND_VERSION="0.1.0"

if [ -f "$VERSION_FILE" ]; then
    BACKEND_VERSION=$(grep '"backend"' "$VERSION_FILE" | sed -E 's/.*"backend"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
    FRONTEND_VERSION=$(grep '"frontend"' "$VERSION_FILE" | sed -E 's/.*"frontend"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
    echo -e "${GREEN}✅ Versions read from .version.json:${NC}"
    echo "   Backend:  $BACKEND_VERSION"
    echo "   Frontend: $FRONTEND_VERSION"
else
    echo -e "${RED}✗ .version.json not found${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found. Run docker-init.sh first:${NC}"
    echo -e "  ${YELLOW}bash scripts/docker-init.sh${NC}"
    exit 1
fi

# Read REGISTRY_OWNER from .env file
REGISTRY_OWNER=$(grep '^REGISTRY_OWNER=' "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$REGISTRY_OWNER" ]; then
    echo -e "${RED}Error: REGISTRY_OWNER not found in .env${NC}"
    exit 1
fi

# Update .env with latest versions
echo -e "${YELLOW}Updating .env with latest versions...${NC}"
sed -i "" "s/^BACKEND_VERSION=.*/BACKEND_VERSION=$BACKEND_VERSION/" "$ENV_FILE" 2>/dev/null || true
sed -i "" "s/^FRONTEND_VERSION=.*/FRONTEND_VERSION=$FRONTEND_VERSION/" "$ENV_FILE" 2>/dev/null || true
echo -e "${GREEN}✅ .env updated${NC}"

echo ""

# Step 2: Check if services are running
echo -e "${YELLOW}⏸️  Checking running services...${NC}"
RUNNING=$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps --services --filter "status=running" 2>/dev/null || echo "")

if [ -n "$RUNNING" ]; then
    echo -e "${YELLOW}Stopping existing services...${NC}"
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" down
    echo -e "${GREEN}✅ Services stopped${NC}"
else
    echo -e "${GREEN}✅ No services running${NC}"
fi

echo ""

# Step 3: Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Services started successfully!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "Access points:"
echo -e "  ${BLUE}Frontend:${NC} http://localhost:9011"
echo -e "  ${BLUE}Backend API:${NC} http://backend:8090 (internal only)"
echo -e "  ${BLUE}API Docs:${NC} http://localhost:9011/api/docs"
echo ""
echo -e "View logs:"
echo -e "  ${BLUE}Backend:${NC}  docker-compose logs -f backend"
echo -e "  ${BLUE}Frontend:${NC} docker-compose logs -f frontend"
echo -e "  ${BLUE}All:${NC}      docker-compose logs -f"
echo ""
