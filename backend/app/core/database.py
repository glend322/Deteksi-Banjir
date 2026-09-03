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
    """Memastikan ekstensi PostGIS aktif di database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            connection.commit()
    except Exception as e:
        print(f"[WARN] Failed to initialize PostGIS extension: {e}")

def get_db():
    """Dependency injector untuk session database pada endpoint FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

