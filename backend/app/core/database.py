from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_postgis():
    """Memastikan ekstensi PostGIS aktif dan kolom skema terbaru ada di database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            # Auto-migrate new columns for users & flood_reports
            connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS trust_score INTEGER DEFAULT 50;"))
            connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_reports INTEGER DEFAULT 0;"))
            connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS verified_reports INTEGER DEFAULT 0;"))
            connection.execute(text("ALTER TABLE flood_reports ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'pending';"))
            connection.execute(text("ALTER TABLE flood_reports ADD COLUMN IF NOT EXISTS confirmations_count INTEGER DEFAULT 0;"))
            connection.commit()
    except Exception as e:
        print(f"[WARN] Failed to initialize PostGIS extension or auto-migrate: {e}")

def get_db():
    """Dependency injector untuk session database pada endpoint FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

