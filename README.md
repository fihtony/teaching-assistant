# English Teaching Assignment Grading System

AI-powered assignment grading for English teachers. Supports multiple question types, auto grading, annotations, and personalized greetings.

## Quick start

```bash
./scripts/start.sh
```

- **Frontend**: http://localhost:3090  
- **Backend API**: http://localhost:8090  
- **API docs**: http://localhost:8090/docs  

## Requirements

- Python 3.9+
- Node.js 18+

## Setup (manual)

```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

Run backend: `cd backend && source venv/bin/activate && python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload`  
Run frontend: `cd frontend && npm run dev` (serves on port 3090)

Stop: `./scripts/stop.sh`

## Project layout

- `backend/` — FastAPI app, services, DB (SQLite)
- `frontend/` — React + TypeScript (Vite)
- `config.yaml` — Server, logging, storage (AI/search/greeting/OCR are in DB)
- `scripts/start.sh`, `scripts/stop.sh` — Start/stop services

## License

MIT License. See [LICENSE](LICENSE).

## Author

**Tony Xu** — fihtony@gmail.com
