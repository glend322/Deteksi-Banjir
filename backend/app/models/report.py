from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.core.database import Base

class FloodReport(Base):
    __tablename__ = "flood_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    location_name = Column(String(255), nullable=False) # e.g. "Jl. Madukoro Raya"
    address = Column(String(255), nullable=True)
    depth_category = Column(String(50), default="20-40 cm") # "< 20 cm", "20-40 cm", "40-70 cm", "> 70 cm"
    depth_cm = Column(Integer, default=30)
    condition = Column(String(50), default="Tergenang") # "Aman", "Waspada", "Tergenang", "Tidak Dapat Dilalui"
    description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)

    # Status Verifikasi AI / Petugas (PRD 6.4)
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(50), default="pending") # pending, verified, unverified, flagged
    verification_note = Column(String(255), nullable=True)
    ai_confidence = Column(Integer, default=0)
    confirmations_count = Column(Integer, default=0) # Konfirmasi / Upvote warga sekitar

    # PostGIS Point (SRID 4326)
    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="reports")

