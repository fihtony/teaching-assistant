#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$PROJECT_DIR/.version.json"
ENV_FILE="$PROJECT_DIR/.env"

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

# Determine registry
echo -e "${YELLOW}Choose where to publish:${NC}"
echo -e "  ${BLUE}1${NC}) GitHub Container Registry (ghcr.io)"
echo -e "  ${BLUE}2${NC}) Local Docker Registry"
echo -e "  ${BLUE}3${NC}) Custom Registry"
read -p "Enter choice (1-3, default: 1): " REGISTRY_CHOICE
REGISTRY_CHOICE=${REGISTRY_CHOICE:-1}

case $REGISTRY_CHOICE in
    1)
        REGISTRY="ghcr.io"
        
        echo -e "\n${YELLOW}GitHub Container Registry selected${NC}"
        echo -e "Registry Owner: ${GREEN}$REGISTRY_OWNER${NC} (from .env)"
        echo -e "Logging in to $REGISTRY..."
        
        # Try to log in using gh CLI
        if command -v gh &> /dev/null; then
            gh auth token | docker login $REGISTRY -u USERNAME --password-stdin
        else
            # Fall back to manual login
            echo "Please log in to Docker to use GHCR:"
            docker login $REGISTRY
        fi
        ;;
    2)
        REGISTRY="localhost:5000"
        # Keep the original registry owner for local registry
        
        echo -e "\n${YELLOW}Local Docker Registry selected${NC}"
        echo -e "Make sure your local registry is running on ${GREEN}$REGISTRY${NC}"
        echo -e "Start it with: ${YELLOW}docker run -d -p 5000:5000 --restart=always --name registry registry:2${NC}"
        ;;
    3)
        read -p "Enter registry URL (e.g., docker.io): " REGISTRY
        read -p "Enter registry owner/username (default: $REGISTRY_OWNER): " CUSTOM_OWNER
        REGISTRY_OWNER="${CUSTOM_OWNER:-$REGISTRY_OWNER}"
        echo "Logging in to $REGISTRY..."
        docker login "$REGISTRY"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${YELLOW}Publishing Teaching Assistant Images${NC}"
echo -e "Backend Version:  ${GREEN}$BACKEND_VERSION${NC}"
echo -e "Frontend Version: ${GREEN}$FRONTEND_VERSION${NC}"
echo -e "Registry:         ${GREEN}$REGISTRY${NC}"
echo -e "Owner:            ${GREEN}$REGISTRY_OWNER${NC}"

# Push backend image
echo -e "\n${YELLOW}Publishing backend image...${NC}"
docker push "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-$BACKEND_VERSION"
docker push "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-latest"
echo -e "${GREEN}✓ Backend image published${NC}"

# Push frontend image
echo -e "\n${YELLOW}Publishing frontend image...${NC}"
docker push "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-$FRONTEND_VERSION"
docker push "$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-latest"
echo -e "${GREEN}✓ Frontend image published${NC}"

# Print summary
echo -e "\n${GREEN}Publish completed successfully!${NC}"
echo -e "\nPublished images:"
echo -e "  Backend:  ${GREEN}$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-$BACKEND_VERSION${NC}"
echo -e "  Frontend: ${GREEN}$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-$FRONTEND_VERSION${NC}"

if [ "$REGISTRY" == "ghcr.io" ]; then
    echo -e "\n${YELLOW}To use these images in docker-compose.yml:${NC}"
    echo -e "  Backend:  ${GREEN}$REGISTRY/$REGISTRY_OWNER/teaching-assistant:backend-$VERSION${NC}"
    echo -e "  Frontend: ${GREEN}$REGISTRY/$REGISTRY_OWNER/teaching-assistant:frontend-$VERSION${NC}"
fi
