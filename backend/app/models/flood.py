from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.core.database import Base

class FloodPoint(Base):
    __tablename__ = "flood_points"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=True) # e.g. "loc-kaligawe"
    name = Column(String(255), nullable=False) # e.g. "Jl. Kaligawe Raya"
    area = Column(String(255), nullable=False) # e.g. "Genuk, Semarang"
    status = Column(String(50), nullable=False, index=True) # safe, watch, flooded, impassable
    status_label = Column(String(100), nullable=True) # "Tidak Dapat Dilalui", "Tergenang", etc.
    depth_cm = Column(Integer, default=0) # Kedalaman genangan air dlm cm
    confidence = Column(Integer, default=100) # Confidence level (0-100%)
    source = Column(String(100), default="CCTV Dinas PU") # CCTV / Laporan Warga / Sensor IoT
    image_url = Column(String(500), nullable=True)
    recommendation = Column(Text, nullable=True)
    cause = Column(String(255), nullable=True)
    vehicles_allowed = Column(JSON, nullable=True) # List string e.g. ["Mobil SUV", "Truk"]

    # PostGIS Point (SRID 4326: WGS84 GPS coordinate)
    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class FloodZone(Base):
    __tablename__ = "flood_zones"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=True) # e.g. "poly-kaligawe"
    name = Column(String(255), nullable=False) # e.g. "Zona Merah Kaligawe - Genuk"
    status = Column(String(50), nullable=False) # impassable, flooded, watch
    fill_color = Column(String(20), default="#3B82F6") # PRD: Fill Biru
    fill_opacity = Column(String(10), default="0.45")
    border_color = Column(String(20), default="#EF4444") # PRD: Outline Merah
    border_weight = Column(Integer, default=3)

    # PostGIS Polygon (SRID 4326)
    geom = Column(Geometry(geometry_type='POLYGON', srid=4326), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class EvacuationPoint(Base):
    __tablename__ = "evacuation_points"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=False) # e.g. "Posko Utama MAJT"
    capacity = Column(String(100), nullable=True) # e.g. "1.200 jiwa"
    supplies = Column(String(255), nullable=True) # e.g. "Dapur umum, medis, genset"
    contact = Column(String(100), nullable=True)
    status = Column(String(100), default="Siap Siaga")

    # PostGIS Point (SRID 4326)
    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

