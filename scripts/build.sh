#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$PROJECT_DIR/.version.json"
ENV_FILE="$PROJECT_DIR/.env"
REGISTRY="${REGISTRY:-ghcr.io}"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo -e "Please run the initialization script first:"
    echo -e "  ${YELLOW}bash scripts/docker-init.sh${NC}"
    exit 1
fi

# Read REGISTRY_OWNER from .env file
REGISTRY_OWNER=$(grep '^REGISTRY_OWNER=' "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$REGISTRY_OWNER" ]; then
    echo -e "${RED}Error: REGISTRY_OWNER not found in .env${NC}"
    exit 1
fi

# Read versions from .version.json
if [ ! -f "$VERSION_FILE" ]; then
    echo -e "${RED}Error: .version.json not found${NC}"
    exit 1
fi

BACKEND_VERSION=$(grep '"backend"' "$VERSION_FILE" | sed -E 's/.*"backend"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
FRONTEND_VERSION=$(grep '"frontend"' "$VERSION_FILE" | sed -E 's/.*"frontend"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')

if [ -z "$BACKEND_VERSION" ] || [ -z "$FRONTEND_VERSION" ]; then
    echo -e "${RED}Error: Failed to read versions from .version.json${NC}"
    exit 1
fi

echo -e "${YELLOW}Building Teaching Assistant Docker Images${NC}"
echo -e "Backend Version:  ${GREEN}$BACKEND_VERSION${NC}"
echo -e "Frontend Version: ${GREEN}$FRONTEND_VERSION${NC}"
echo -e "Registry:         ${GREEN}$REGISTRY${NC}"
echo -e "Owner:            ${GREEN}$REGISTRY_OWNER${NC}"

# Build backend image
echo -e "\n${YELLOW}Building backend image...${NC}"
docker build \
    --tag "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-$BACKEND_VERSION" \
    --tag "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-latest" \
    --file "$PROJECT_DIR/backend/Dockerfile" \
    "$PROJECT_DIR/backend"

echo -e "${GREEN}✓ Backend image built successfully${NC}"

# Build frontend image
echo -e "\n${YELLOW}Building frontend image...${NC}"
docker build \
    --tag "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-$FRONTEND_VERSION" \
    --tag "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-latest" \
    --file "$PROJECT_DIR/frontend/Dockerfile" \
    "$PROJECT_DIR/frontend"

echo -e "${GREEN}✓ Frontend image built successfully${NC}"

# Print summary
echo -e "\n${GREEN}Build completed successfully!${NC}"
echo -e "\nBuilt images:"
echo -e "  Backend:  ${GREEN}$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-$BACKEND_VERSION${NC}"
echo -e "  Frontend: ${GREEN}$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-$FRONTEND_VERSION${NC}"

echo -e "\nTo push to registry, run:"
echo -e "  ${YELLOW}./scripts/publish.sh${NC}"

echo -e "\nTo launch locally, run:"
echo -e "  ${YELLOW}./scripts/launch.sh${NC}"
