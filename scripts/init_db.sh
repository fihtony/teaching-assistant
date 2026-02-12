#!/bin/bash

# ===============================================
# Initialize database (run once before first app launch)
# ===============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "Initializing database..."
echo "  Backend: $BACKEND_DIR"
echo ""

cd "$BACKEND_DIR"
python3 -m scripts.init_db

echo ""
echo "Done. Start the app with: ./scripts/start.sh (or run uvicorn from backend/)"
