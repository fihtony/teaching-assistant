# English Teaching Assignment Grading System

AI-powered assignment grading for English teachers. Supports multiple question types, auto grading, annotations, and personalized greetings.

## Quick Start

### Local Development

```bash
./scripts/start.sh
```

Frontend: http://localhost:3090 | Backend: http://localhost:8090 | Docs: http://localhost:8090/docs

### Docker Container

```bash
docker-compose up -d
```

Frontend: http://localhost:9011 | Backend: http://localhost:8090 (internal only)

---

## Build Docker Images

### Build Backend

```bash
cd backend
docker build --tag ghcr.io/$REGISTRY_OWNER/teaching-assistant:backend-0.1.1 .
```

### Build Frontend

```bash
cd frontend
docker build --tag ghcr.io/$REGISTRY_OWNER/teaching-assistant:frontend-0.1.1 .
```

### Build Both

```bash
./scripts/build.sh
```

---

## Docker Compose Setup

### Initialize Environment (macOS)

```bash
bash scripts/docker-init.sh
```

This creates:

- `.env` file with your macOS username and paths
- Data folder: `~/apps/teaching-assistant/data`
- Logs folder: `~/apps/teaching-assistant/logs`

### Alternative: Manual Setup

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
# REGISTRY_OWNER=your-username
# DATA_PATH=${HOME}/apps/teaching-assistant/data
# LOGS_PATH=${HOME}/apps/teaching-assistant/logs

# Create folders
mkdir -p ~/apps/teaching-assistant/data
mkdir -p ~/apps/teaching-assistant/logs
```

### Start Services

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Stop Services

```bash
docker-compose down
```

### Stop & Remove Volumes

```bash
docker-compose down -v
```

### Folder Mounting

```yaml
Host Path                                   Container Path
~/apps/teaching-assistant/data       →      /app/data
~/apps/teaching-assistant/logs       →      /app/logs
```

### Verify Mount

```bash
# Check from container
docker-compose exec backend ls -la /app/data

# Check from host
ls -la ~/apps/teaching-assistant/data
```

---

## Local Development Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database

```bash
./scripts/init_db.sh
```

---

## Project Structure

- `backend/` — FastAPI, services, SQLite DB
- `frontend/` — React + TypeScript + Vite
- `config.yaml` — Server, logging, storage config
- `data/` — Database and uploads (gitignored)
- `logs/` — Application logs (gitignored)
- `scripts/` — Start/stop/build helpers

---

## Security

- Do not commit `.env` or API keys
- Use environment variables for secrets
- Set `TEACHING_ENCRYPTION_KEY` in production
- Keep `data/`, `logs/`, `.env` out of repo

---

## License

MIT License. See [LICENSE](LICENSE).

## Author

**Tony Xu** — tony@tarch.ca
