#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
PACKAGE_NAME="teaching-assistant"

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed.${NC}"
    echo -e "Install it from: ${BLUE}https://cli.github.com${NC}"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null 2>&1; then
    echo -e "${RED}Error: Not authenticated with GitHub CLI.${NC}"
    echo -e "Run: ${YELLOW}gh auth login${NC}"
    exit 1
fi

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

# Determine if owner is a user or organization
OWNER_TYPE="user"
if gh api "/orgs/$REGISTRY_OWNER" &> /dev/null 2>&1; then
    OWNER_TYPE="org"
fi

# Build the base API path
if [ "$OWNER_TYPE" == "org" ]; then
    API_BASE="/orgs/$REGISTRY_OWNER/packages/container/$PACKAGE_NAME"
else
    API_BASE="/user/packages/container/$PACKAGE_NAME"
fi

# Function to list all package versions
list_packages() {
    echo -e "${YELLOW}Fetching package versions for ${CYAN}$REGISTRY_OWNER/$PACKAGE_NAME${NC}...\n"

    # Fetch package versions
    VERSIONS=$(gh api "$API_BASE/versions" --paginate 2>/dev/null) || {
        echo -e "${RED}Error: Could not fetch package versions.${NC}"
        echo -e "Make sure the package ${CYAN}$PACKAGE_NAME${NC} exists under ${CYAN}$REGISTRY_OWNER${NC}."
        echo -e "You can view packages at: ${BLUE}https://github.com/$REGISTRY_OWNER?tab=packages${NC}"
        exit 1
    }

    COUNT=$(echo "$VERSIONS" | python3 -c "import json,sys; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0")

    if [ "$COUNT" == "0" ]; then
        echo -e "${YELLOW}No package versions found.${NC}"
        return
    fi

    echo -e "${GREEN}Found $COUNT package version(s):${NC}\n"
    printf "%-10s %-45s %s\n" "ID" "TAGS" "CREATED"
    printf "%-10s %-45s %s\n" "----------" "---------------------------------------------" "--------------------"

    echo "$VERSIONS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data:
    vid = str(v.get('id', ''))
    tags = ', '.join(v.get('metadata', {}).get('container', {}).get('tags', [])) or '(untagged)'
    created = v.get('created_at', '')[:10] if v.get('created_at') else ''
    print(f'{vid:<10} {tags:<45} {created}')
"

    echo ""
    echo -e "${BLUE}View packages online:${NC}"
    echo -e "  ${CYAN}https://github.com/$REGISTRY_OWNER/packages/container/$PACKAGE_NAME/versions${NC}"
    echo -e "\n${BLUE}Note:${NC} Package sizes are visible on the GitHub Packages page above."
}

# Function to delete a specific package version
delete_version() {
    local VERSION_ID="$1"

    if [ -z "$VERSION_ID" ]; then
        echo -e "${RED}Error: No version ID specified.${NC}"
        echo -e "Usage: ${YELLOW}$0 delete <version_id>${NC}"
        echo -e "Run ${YELLOW}$0 list${NC} to see available version IDs."
        exit 1
    fi

    # Confirm deletion
    echo -e "${RED}WARNING: This will permanently delete package version ID: $VERSION_ID${NC}"
    read -p "Are you sure you want to delete this version? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Deletion cancelled.${NC}"
        exit 0
    fi

    echo -e "\n${YELLOW}Deleting version $VERSION_ID...${NC}"
    gh api --method DELETE "$API_BASE/versions/$VERSION_ID" && {
        echo -e "${GREEN}✓ Package version $VERSION_ID deleted successfully.${NC}"
    } || {
        echo -e "${RED}Error: Failed to delete version $VERSION_ID.${NC}"
        echo -e "Make sure you have the required permissions (delete:packages scope)."
        exit 1
    }
}

# Function to delete all untagged versions
delete_untagged() {
    echo -e "${YELLOW}Fetching untagged package versions...${NC}"

    VERSIONS=$(gh api "$API_BASE/versions" --paginate 2>/dev/null) || {
        echo -e "${RED}Error: Could not fetch package versions.${NC}"
        exit 1
    }

    UNTAGGED_IDS=$(echo "$VERSIONS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data:
    tags = v.get('metadata', {}).get('container', {}).get('tags', [])
    if not tags:
        print(v['id'])
")

    if [ -z "$UNTAGGED_IDS" ]; then
        echo -e "${GREEN}No untagged versions found.${NC}"
        return
    fi

    COUNT=$(echo "$UNTAGGED_IDS" | wc -l | tr -d ' ')
    echo -e "${RED}WARNING: This will permanently delete $COUNT untagged package version(s).${NC}"
    read -p "Are you sure you want to delete all untagged versions? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Deletion cancelled.${NC}"
        exit 0
    fi

    echo "$UNTAGGED_IDS" | while read -r VID; do
        if [ -n "$VID" ]; then
            echo -e "  Deleting version $VID..."
            gh api --method DELETE "$API_BASE/versions/$VID" && \
                echo -e "  ${GREEN}✓ Deleted version $VID${NC}" || \
                echo -e "  ${RED}✗ Failed to delete version $VID${NC}"
        fi
    done

    echo -e "\n${GREEN}Cleanup complete.${NC}"
}

# Main menu
show_usage() {
    echo -e "${YELLOW}Teaching Assistant — Package Manager${NC}"
    echo -e "Manage GitHub Container Registry packages for ${CYAN}$REGISTRY_OWNER/$PACKAGE_NAME${NC}\n"
    echo -e "Usage: ${YELLOW}$0 <command>${NC}\n"
    echo -e "Commands:"
    echo -e "  ${BLUE}list${NC}                List all package versions with creation dates"
    echo -e "  ${BLUE}delete <id>${NC}         Delete a specific package version by ID"
    echo -e "  ${BLUE}delete-untagged${NC}     Delete all untagged (dangling) package versions"
    echo -e ""
    echo -e "View package sizes online:"
    echo -e "  ${CYAN}https://github.com/$REGISTRY_OWNER/packages/container/$PACKAGE_NAME/versions${NC}"
}

case "${1:-}" in
    list)
        list_packages
        ;;
    delete)
        delete_version "${2:-}"
        ;;
    delete-untagged)
        delete_untagged
        ;;
    *)
        show_usage
        ;;
esac
