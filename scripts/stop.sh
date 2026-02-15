#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

echo -e "${YELLOW}Stopping and removing Teaching Assistant containers...${NC}"

# Stop and remove containers
docker-compose -f "$DOCKER_COMPOSE_FILE" down

echo -e "${GREEN}✓ Containers stopped and removed${NC}"

# Ask if user wants to remove volumes
read -p "Do you want to remove volumes? (y/n, default: n): " REMOVE_VOLUMES
if [ "$REMOVE_VOLUMES" == "y" ] || [ "$REMOVE_VOLUMES" == "Y" ]; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v
    echo -e "${GREEN}✓ Volumes removed${NC}"
fi

echo -e "\n${GREEN}Cleanup completed!${NC}"
