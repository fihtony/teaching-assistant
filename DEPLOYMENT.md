# Deployment Guide

This guide explains how to deploy Teaching Assistant Grading System using Docker and GitHub Actions.

## Automatic Builds

### Triggered by Push to Main Branch
When you push to `main` branch, the CI/CD pipeline automatically:
1. Runs lint and security checks
2. Detects which projects changed (backend/frontend)
3. Builds Docker images for changed projects only
4. Supports multiple architectures:
   - **linux/amd64** (default x86_64 servers)
   - **darwin/arm64** (ARM64 for macOS Apple Silicon)
5. Creates a GitHub release with all image tags

### Triggered by Pull Request
When you create/update a PR to `main` branch, the CI/CD pipeline:
1. Runs lint and security checks
2. Builds images for **both platforms** (linux/amd64 and darwin/arm64)
3. Does NOT create releases or push images (for testing only)

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
  - Shows backend version input only
  - Uses backend version from input or .version.json
- `frontend` - Build only frontend images
  - Shows frontend version input only
  - Uses frontend version from input or .version.json
- `both` - Build both backend and frontend images
  - Shows both backend and frontend version inputs
  - Uses versions from inputs or .version.json

**Backend Version** (Optional - shown only for backend/both)
- Leave empty to use version from `.version.json` (default: **0.1.0**)
- Or specify a custom version (e.g., `0.2.0`)

**Frontend Version** (Optional - shown only for frontend/both)
- Leave empty to use version from `.version.json` (default: **0.1.0**)
- Or specify a custom version (e.g., `0.2.0`)

**Platforms** (Required)
- `linux-amd64` - Build for Linux x86_64 (default servers)
  - Best for: AWS EC2, DigitalOcean, Google Cloud, standard VPS
  - Images tagged: `-amd64`
- `darwin-arm64` - Build for macOS Apple Silicon
  - Best for: Mac computers, MacStadium, AWS Graviton Mac
  - Images tagged: `-darwin-arm64` (uses linux/arm64 base)
- `both` - Build for both platforms (default for PR)
  - Slower but supports all use cases

### Step 3: Trigger Build
Click **Run workflow** to start the build process.

## Docker Images

### Available Tags

#### Backend Images
- `ghcr.io/fihtony/teaching-assistant:backend-<version>-amd64` - Linux x86_64
- `ghcr.io/fihtony/teaching-assistant:backend-<version>-arm64` - Linux ARM64 (macOS)
- `ghcr.io/fihtony/teaching-assistant:backend-latest` - Latest AMD64

#### Frontend Images
- `ghcr.io/fihtony/teaching-assistant:frontend-<version>-amd64` - Linux x86_64
- `ghcr.io/fihtony/teaching-assistant:frontend-<version>-arm64` - Linux ARM64 (macOS)
- `ghcr.io/fihtony/teaching-assistant:frontend-latest` - Latest AMD64

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

# Use default platform (Linux x86_64)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker Compose on macOS Apple Silicon

```bash
# Set platform for macOS Apple Silicon
export PLATFORM=darwin-arm64        # Image tag suffix
export PLATFORM_LINUX=linux/arm64     # Docker platform for arm64 images

# Start services
docker-compose up -d

# This will use:
# - backend-latest-darwin-arm64 (linux/arm64 platform)
# - frontend-latest-darwin-arm64 (linux/arm64 platform)
```

### Using Docker Compose on Linux ARM64

```bash
# Set platform for Linux ARM64
export PLATFORM=arm64             # Image tag suffix
export PLATFORM_LINUX=linux/arm64   # Docker platform for arm64 images

# Start services
docker-compose up -d

# This will use:
# - backend-latest-arm64 (linux/arm64 platform)
# - frontend-latest-arm64 (linux/arm64 platform)
```

## Version Management

### Version Format

Use semantic versioning (MAJOR.MINOR.PATCH):
- `0.1.0` - Initial release
- `0.1.1` - Bug fix (PATCH increment)
- `0.2.0` - New feature (MINOR increment)
- `1.0.0` - Major breaking change (MAJOR increment)

### Current Versions

Current versions in `.version.json`:

```json
{
  "backend": "0.1.0",
  "frontend": "0.1.0"
}
```

### Update Version for Build

To use a specific version in manual builds:

1. Update `.version.json`:
```bash
vim .version.json
```

2. Commit and push:
```bash
git add .version.json
git commit -m "chore: update versions to 0.2.0"
git push origin main
```

3. Trigger workflow with versions from `.version.json` (leave version inputs empty)

Or, **skip updating .version.json** and directly specify version in the workflow form.

## Platform Selection Guide

### When to Use Each Platform

| Platform | Use Case | Image Tag |
|----------|-----------|------------|
| **linux/amd64** | Default servers, cloud VMs, CI/CD | `-amd64` |
| **darwin/arm64** | macOS Apple Silicon (M1/M2/M3) | `-darwin-arm64` |

### Platform Examples

**Example 1: Deploying to standard Linux server**
```bash
# Use default (no PLATFORM variable needed)
docker-compose up -d
```

**Example 2: Deploying to macOS Apple Silicon**
```bash
export PLATFORM=darwin-arm64
export PLATFORM_LINUX=linux/arm64
docker-compose up -d
```

**Example 3: Manual build for both platforms**
```bash
# From GitHub Actions:
# Build Target: both
# Platforms: both
# Backend Version: 0.2.0
# Frontend Version: 0.2.0
```

## Troubleshooting

### Build Fails on macOS Apple Silicon

If Docker Desktop is running on macOS Apple Silicon:

1. Make sure Docker Desktop is running
2. Use the `darwin-arm64` platform option in builds
3. For local deployment, set `PLATFORM=darwin-arm64` and `PLATFORM_LINUX=linux/arm64`

### Images Not Pulling

```bash
# Login to GitHub Container Registry
echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# Or use Personal Access Token
docker login ghcr.io -u YOUR_USERNAME --password-stdin <<< YOUR_TOKEN
```

### Platform Mismatch Error

If you see "no matching manifest" error:

```bash
# Check your architecture
uname -m

# Linux x86_64:
#   Use -amd64 images

# Linux ARM64 or macOS Apple Silicon:
#   Use -darwin-arm64 images

# Example:
export PLATFORM=darwin-arm64
export PLATFORM_LINUX=linux/arm64
docker-compose up -d
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
┌─────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                      │
└─────────────────────────────────────────────────────────┘
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
    │  Backend │   │ Frontend │   │  Backend  │
    │   Build  │   │  Build   │   │   Build   │
    │ (amd64)  │   │ (amd64)  │   │(arm64)   │
    └────┬─────┘   └────┬─────┘   └────┬───────┘
         │               │               │
         │      ┌────────┴────┐        │
         │      │   Backend    │        │
         │      │   Build     │        │
         │      │ (arm64)    │        │
         │      └─────┬───────┘        │
         └───────────┴──────┬──────────┴───┐
                            │             │
                     ┌──────────────┴──────┐
                     │ Create Release           │
                     └───────┬─────────────┘
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
