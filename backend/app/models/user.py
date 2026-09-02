from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Spesifikasi Kendaraan (PRD 5.1 & Catatan Tambahan)
    vehicle_type = Column(String(100), default="Mobil (City Car)") # Motor, Mobil Sedan, Mobil SUV, Truk
    vehicle_max_depth_cm = Column(Integer, default=30) # Batas kedalaman air maksimum
    
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    saved_locations = relationship("SavedLocation", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("FloodReport", back_populates="user")
    trips = relationship("TripHistory", back_populates="user", cascade="all, delete-orphan")


class SavedLocation(Base):
    __tablename__ = "saved_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False) # e.g. "Rumah", "Kantor", "Kampus"
    address = Column(String(255), nullable=True)
    icon = Column(String(50), default="map-pin")
    
    # Koordinat Spasial PostGIS
    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="saved_locations")


class TripHistory(Base):
    __tablename__ = "trip_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    origin_name = Column(String(255), nullable=False)
    destination_name = Column(String(255), nullable=False)
    duration_str = Column(String(50), nullable=True) # e.g. "34 menit"
    distance_km = Column(Float, nullable=True)
    route_type = Column(String(50), default="Rute Teraman")
    status = Column(String(100), default="Berhasil Menghindar Banjir")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="trips")

