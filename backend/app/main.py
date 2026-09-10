import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

from app.core.config import settings
from app.core.database import Base, engine, init_postgis
from app.core.scheduler import start_background_scheduler, stop_background_scheduler
from app.core.logging_middleware import RequestLoggingMiddleware
from app.core.rate_limiter import limiter
from app.api.router import api_router

# Konfigurasi logging dasar
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Inisialisasi DB & Background Scheduler
    try:
        init_postgis()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database diinisialisasi.")
    except Exception as e:
        logger.warning(f"[WARN] Database initialization note: {e}")

    start_background_scheduler()
    logger.info("🚀 SafeRoute Semarang API siap.")
    yield
    # Shutdown: Matikan Background Scheduler
    stop_background_scheduler()
    logger.info("🛑 SafeRoute Semarang API dimatikan.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API Sistem Deteksi Banjir & Rekomendasi Rute Aman Kota Semarang",
    version="1.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Rate Limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request Logging Middleware (P3.4)
app.add_middleware(RequestLoggingMiddleware)

# Konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount direktori uploads foto laporan
upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# Registrasi Router API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "app": "SafeRoute Semarang API",
        "version": "1.1.0",
        "status": "online",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint (P3.5).
    Memeriksa status komponen utama: database, konfigurasi, dan scheduler.
    """
    from app.core.database import SessionLocal
    from app.core.scheduler import _scheduler

    db_status = "ok"
    db_error = None
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    scheduler_status = "running" if _scheduler and _scheduler.running else "stopped"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "version": "1.1.0",
        "components": {
            "database": {"status": db_status, "error": db_error},
            "scheduler": {"status": scheduler_status},
            "modeling_api_url": settings.MODELING_API_URL,
            "osrm_url": settings.OSRM_BASE_URL,
        }
    }
