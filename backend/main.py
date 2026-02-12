"""
English Teaching Assignment Grading System - Backend Application

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_config, get_log_path, get_storage_path
from app.core.logging import setup_logging, get_logger
from app.api import api_router


# Record startup time globally
_startup_time = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Initializes resources on startup and cleans up on shutdown.
    """
    # Startup
    global _startup_time
    _startup_time = datetime.utcnow().isoformat()
    logger = setup_logging()
    log_path = get_log_path()
    logger.info("Starting English Teaching Assignment Grading System...")
    logger.debug("Log level: %s, log file: %s", get_config().logging.level, log_path)

    # Do not init or migrate database on startup; run init-db script once manually.

    # Ensure storage directories exist
    for storage_type in ["uploads", "graded", "templates", "cache"]:
        path = get_storage_path(storage_type)
        logger.info(f"Storage directory ready: {path}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title="English Teaching Assignment Grading System",
    description="AI-powered assignment grading system for English teachers",
    version="0.1.0",
    lifespan=lifespan,
)

# Request logging middleware (flow-wise: log each request and response)
@app.middleware("http")
async def log_requests(request, call_next):
    logger = get_logger()
    method = request.method
    path = request.url.path
    logger.debug("Request started: %s %s", method, path)
    response = await call_next(request)
    logger.debug("Request completed: %s %s -> %s", method, path, response.status_code)
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3090",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3090",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": "English Teaching Assignment Grading System",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with startup time."""
    return {
        "status": "healthy",
        "startup_time": _startup_time,
        "startup_timestamp": _startup_time,  # Same as startup_time for clarity
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
    )
