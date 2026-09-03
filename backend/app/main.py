from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import Base, engine, init_postgis
from app.api.router import api_router

# Inisialisasi PostGIS & Skema Database
try:
    init_postgis()
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[WARN] Database initialization note (will retry on connection): {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API Sistem Deteksi Banjir & Rekomendasi Rute Aman Kota Semarang",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
        "status": "online",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }

