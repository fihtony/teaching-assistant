#!/bin/bash
# Initialize docker-compose environment on macOS
# Creates .env file with versions from .version.json and data folders

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
ENV_FILE="$PROJECT_ROOT/.env"
VERSION_FILE="$PROJECT_ROOT/.version.json"
APP_NAME="teaching-assistant"

echo "🚀 Setting up Teaching Assistant Docker Environment"
echo "=================================================="

# Get macOS username for REGISTRY_OWNER
MAC_USER=$(whoami)
HOME_DIR=$HOME
APP_NAME="teaching-assistant"
DATA_PATH="$HOME_DIR/apps/$APP_NAME/data"
LOGS_PATH="$HOME_DIR/apps/$APP_NAME/logs"
REGISTRY_OWNER="$MAC_USER"

# Read versions from .version.json
BACKEND_VERSION="0.1.0"
FRONTEND_VERSION="0.1.0"

if [ -f "$VERSION_FILE" ]; then
    BACKEND_VERSION=$(grep '"backend"' "$VERSION_FILE" | sed -E 's/.*"backend"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
    FRONTEND_VERSION=$(grep '"frontend"' "$VERSION_FILE" | sed -E 's/.*"frontend"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
fi

# Check if .env exists
if [ -f "$ENV_FILE" ]; then
    echo "✅ .env file exists, updating versions..."
    # Update versions in existing .env
    sed -i "" "s/^BACKEND_VERSION=.*/BACKEND_VERSION=$BACKEND_VERSION/" "$ENV_FILE" 2>/dev/null || true
    sed -i "" "s/^FRONTEND_VERSION=.*/FRONTEND_VERSION=$FRONTEND_VERSION/" "$ENV_FILE" 2>/dev/null || true
else
    echo "📝 Creating .env file..."
    
    # Create .env file with actual paths and versions from .version.json
    cat > "$ENV_FILE" << EOF
# Docker Compose Environment Variables
# Auto-generated on $(date)
# Versions from .version.json

REGISTRY_OWNER=$REGISTRY_OWNER
BACKEND_VERSION=$BACKEND_VERSION
FRONTEND_VERSION=$FRONTEND_VERSION
DATA_PATH=$DATA_PATH
LOGS_PATH=$LOGS_PATH
EOF
    
    chmod 600 "$ENV_FILE"
    echo "✅ .env created"
fi

# Create data and logs directories
echo "📁 Creating data folders..."
DATA_PATH=$(grep '^DATA_PATH=' "$ENV_FILE" | cut -d'=' -f2)
LOGS_PATH=$(grep '^LOGS_PATH=' "$ENV_FILE" | cut -d'=' -f2)

mkdir -p "$DATA_PATH" "$LOGS_PATH"
chmod 755 "$DATA_PATH" "$LOGS_PATH"
echo "✅ Folders created"

# Display completion info
echo ""
echo "✅ Setup complete! Ready to run:"
echo ""
echo "   docker-compose up -d"
echo ""
echo "Access points:"
echo "   Frontend: http://localhost:9011"
echo "   Backend:  http://localhost:8090 (internal only)"
echo "   Docs:     http://localhost:8090/docs"
echo ""
