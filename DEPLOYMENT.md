# Deployment Guide

This guide explains how to deploy the Teaching Assistant Grading System using Docker and GitHub Actions.

## Automatic Builds

### Triggered by Push to Main Branch
When you push to the `main` branch, the CI/CD pipeline automatically:
1. Runs lint and security checks
2. Detects which projects changed (backend/frontend)
3. Builds Docker images for changed projects only
4. Supports multiple architectures:
   - **linux/amd64** (default x86_64 servers)
   - **linux/arm64** (ARM servers like Raspberry Pi, AWS Graviton)
   - **darwin/arm64** (macOS Apple Silicon)
5. Creates a GitHub release with all image tags

## Manual Builds (Workflow Dispatch)

You can manually trigger builds from GitHub Actions UI:

### Step 1: Navigate to Actions
1. Go to your repository on GitHub
2. Click on **Actions** tab
3. Select **CI/CD Pipeline** workflow
4. Click **Run workflow** button

### Step 2: Configure Build Parameters

**Build Target** (Required)
- `backend` - Build only backend images
- `frontend` - Build only frontend images
- `both` - Build both backend and frontend images

**Backend Version** (Optional)
- Leave empty to use version from `.version.json`
- Or specify a custom version (e.g., `0.2.0`)

**Frontend Version** (Optional)
- Leave empty to use version from `.version.json`
- Or specify a custom version (e.g., `0.2.0`)

### Step 3: Trigger Build
Click **Run workflow** to start the build process.

## Docker Images

### Available Tags

#### Backend Images
- `ghcr.io/fihtony/teaching-assistant:backend-<version>-amd64` - Linux x86_64
- `ghcr.io/fihtony/teaching-assistant:backend-<version>-arm64` - Linux ARM64
- `ghcr.io/fihtony/teaching-assistant:backend-<version>-darwin-arm64` - macOS Apple Silicon
- `ghcr.io/fihtony/teaching-assistant:backend-latest` - Latest (amd64)
- `ghcr.io/fihtony/teaching-assistant:backend-latest-arm64` - Latest ARM64
- `ghcr.io/fihtony/teaching-assistant:backend-latest-darwin-arm64` - Latest macOS

#### Frontend Images
- `ghcr.io/fihtony/teaching-assistant:frontend-<version>-amd64` - Linux x86_64
- `ghcr.io/fihtony/teaching-assistant:frontend-<version>-arm64` - Linux ARM64
- `ghcr.io/fihtony/teaching-assistant:frontend-<version>-darwin-arm64` - macOS Apple Silicon
- `ghcr.io/fihtony/teaching-assistant:frontend-latest` - Latest (amd64)
- `ghcr.io/fihtony/teaching-assistant:frontend-latest-arm64` - Latest ARM64
- `ghcr.io/fihtony/teaching-assistant:frontend-latest-darwin-arm64` - Latest macOS

### Pull Images

```bash
# Pull specific version for your platform
docker pull ghcr.io/fihtony/teaching-assistant:backend-0.1.0-amd64
docker pull ghcr.io/fihtony/teaching-assistant:frontend-0.1.0-amd64

# Pull latest
docker pull ghcr.io/fihtony/teaching-assistant:backend-latest
docker pull ghcr.io/fihtony/teaching-assistant:frontend-latest
```

## Local Deployment

### Using Docker Compose (Default - Linux AMD64)

```bash
# Clone the repository
git clone https://github.com/fihtony/teaching-assistant.git
cd teaching-assistant

# Set environment variables (optional)
export REGISTRY_OWNER=fihtony
export BACKEND_VERSION=0.1.0
export FRONTEND_VERSION=0.1.0
export DATA_PATH=./data
export LOGS_PATH=./logs
export FRONTEND_PORT=9011

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker Compose on macOS Apple Silicon

Create an override file for Apple Silicon:

```bash
# Create docker-compose.darwin-arm64.override.yml
cat > docker-compose.darwin-arm64.override.yml <<EOF
services:
  backend:
    image: ghcr.io/fihtony/teaching-assistant:backend-\${BACKEND_VERSION:-latest}-darwin-arm64
    platform: linux/arm64
  frontend:
    image: ghcr.io/fihtony/teaching-assistant:frontend-\${FRONTEND_VERSION:-latest}-darwin-arm64
    platform: linux/arm64
EOF

# Start with override
docker-compose -f docker-compose.yml -f docker-compose.darwin-arm64.override.yml up -d
```

### Using Docker Compose on Linux ARM64

Create an override file for ARM64:

```bash
# Create docker-compose.arm64.override.yml
cat > docker-compose.arm64.override.yml <<EOF
services:
  backend:
    image: ghcr.io/fihtony/teaching-assistant:backend-\${BACKEND_VERSION:-latest}-arm64
    platform: linux/arm64
  frontend:
    image: ghcr.io/fihtony/teaching-assistant:frontend-\${FRONTEND_VERSION:-latest}-arm64
    platform: linux/arm64
EOF

# Start with override
docker-compose -f docker-compose.yml -f docker-compose.arm64.override.yml up -d
```

## Version Management

### Update Version

Version numbers are stored in `.version.json`:

```json
{
  "backend": "0.1.0",
  "frontend": "0.1.0"
}
```

To update a version:

```bash
# Edit .version.json
vim .version.json

# Commit and push
git add .version.json
git commit -m "chore: update versions to 0.2.0"
git push origin main
```

**Note:** The CI/CD pipeline does NOT auto-increment versions. You must update versions manually before triggering builds.

### Version Format

Use semantic versioning (MAJOR.MINOR.PATCH):
- `0.1.0` - Initial release
- `0.1.1` - Bug fix
- `0.2.0` - New feature
- `1.0.0` - Major breaking change

## Troubleshooting

### Build Fails on macOS Apple Silicon

If Docker Desktop is running on macOS Apple Silicon:

1. Make sure Docker Desktop is running
2. Enable "Use Rosetta for x86/amd64 emulation" in Docker Desktop settings if needed
3. Or use the `-darwin-arm64` tagged images built for ARM64

### Images Not Pulling

```bash
# Login to GitHub Container Registry
echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# Or use Personal Access Token
docker login ghcr.io -u YOUR_USERNAME --password-stdin <<< YOUR_TOKEN
```

### Port Already in Use

```bash
# Change frontend port in docker-compose.yml
# Or use environment variable
export FRONTEND_PORT=9012
docker-compose up -d
```

## CI/CD Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                      │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────┼─────────────┐
        │             │             │
    ┌───▼───┐    │      ┌────▼─────┐
    │   Lint  │    │      │  Version  │
    │ & Check │    │      │  Format   │
    └────┬────┘    │      └────┬─────┘
         │           │           │
         └───────────┴─────┬───┴───┐
                             │         │
                    ┌────────┴────────┐
                    │ Determine Build │
                    │    Targets    │
                    └────┬───────┬───┘
         ┌──────────────┼────────┼──────────────┐
         │              │         │              │
    ┌────▼────┐   ┌────▼────┐   ┌────────▼──┐
    │  Backend │   │ Frontend │   │   Backend  │
    │   Build  │   │  Build   │   │   Build   │
    │  (amd64) │   │ (amd64)  │   │  (arm64)  │
    └────┬─────┘   └────┬─────┘   └────┬───────┘
         │               │               │
         │      ┌────────┴────┐        │
         │      │   Backend    │        │
         │      │   Build     │        │
         │      │ (arm64)    │        │
         │      └─────┬───────┘        │
         └───────────┴──────┬──────────┴┐
                            │             │
                     ┌────────┴────────┐
                     │ Create Release  │
                     └───────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Test Images  │
                    └────────┬────────┘
                             │
                       ┌────────▼────────┐
                       │  Deploy to     │
                       │  Production    │
                       └────────────────┘
```

## Support

For issues or questions:
- Open an issue on GitHub
- Check GitHub Actions logs for build errors
- Verify Docker logs: `docker-compose logs`
