from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.flood import FloodPoint
from app.models.weather import Alert

router = APIRouter()

class AIPredictionPayload(BaseModel):
    source_name: str = Field(..., description="e.g. CCTV Kaligawe, Model YOLOv8, AI Drone")
    location_name: str
    area: str
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    estimated_depth_cm: int = Field(..., ge=0)
    confidence: int = Field(..., ge=0, le=100)
    photo_url: Optional[str] = None
    prediction_type: str = "computer_vision"
    cause: Optional[str] = None
    alert_needed: bool = False
    alert_title: Optional[str] = None
    alert_subtext: Optional[str] = None

class AIPredictionResponse(BaseModel):
    status: str
    message: str
    flood_point_id: int
    alert_id: Optional[int] = None
    confidence: int

@router.post("/predictions", response_model=AIPredictionResponse, status_code=status.HTTP_201_CREATED, summary="Push Hasil Deteksi AI / CCTV ke Peta")
def receive_ai_prediction(
    payload: AIPredictionPayload,
    db: Session = Depends(get_db)
):
    """
    Endpoint Internal untuk Tim AI / ML:
    Model Computer Vision / Prediksi Banjir menyuntikkan hasil deteksi langsung ke database PostGIS.
    """
    if payload.estimated_depth_cm >= 40:
        status_val = "impassable"
        status_lbl = "Tidak Dapat Dilalui"
    elif payload.estimated_depth_cm >= 20:
        status_val = "flooded"
        status_lbl = "Tergenang"
    elif payload.estimated_depth_cm > 0:
        status_val = "watch"
        status_lbl = "Waspada"
    else:
        status_val = "safe"
        status_lbl = "Aman"

    geom = from_shape(Point(payload.lng, payload.lat), srid=4326)

    # Cek apakah titik dengan nama serupa sudah ada
    existing_point = db.query(FloodPoint).filter(FloodPoint.name == payload.location_name).first()
    if existing_point:
        existing_point.status = status_val
        existing_point.status_label = status_lbl
        existing_point.depth_cm = payload.estimated_depth_cm
        existing_point.confidence = payload.confidence
        existing_point.source = f"{payload.source_name} (AI)"
        if payload.photo_url:
            existing_point.image_url = payload.photo_url
        if payload.cause:
            existing_point.cause = payload.cause
        point_id = existing_point.id
    else:
        new_point = FloodPoint(
            slug=f"loc-ai-{int(payload.lat*1000)}-{int(payload.lng*1000)}",
            name=payload.location_name,
            area=payload.area,
            status=status_val,
            status_label=status_lbl,
            depth_cm=payload.estimated_depth_cm,
            confidence=payload.confidence,
            source=f"{payload.source_name} (AI)",
            image_url=payload.photo_url or "/assets/cctv_kaligawe.jpg",
            recommendation=f"Deteksi AI: Kedalaman {payload.estimated_depth_cm} cm. Berhati-hati melintas.",
            cause=payload.cause or "Deteksi Genangan Air AI",
            vehicles_allowed=["Mobil SUV", "Truk"] if status_val != "impassable" else ["Hanya SAR"],
            geom=geom
        )
        db.add(new_point)
        db.flush()
        point_id = new_point.id

    # Jika butuh peringatan dini, buat alert baru
    alert_id = None
    if payload.alert_needed or payload.estimated_depth_cm >= 40:
        alert = Alert(
            slug=f"alert-ai-{point_id}-{int(datetime.now().timestamp())}",
            category="urgent" if payload.estimated_depth_cm >= 40 else "warning",
            title=payload.alert_title or f"Peringatan Banjir AI: {payload.location_name}",
            location=payload.location_name,
            subtext=payload.alert_subtext or f"Deteksi genangan {payload.estimated_depth_cm} cm (Confidence {payload.confidence}%). Hindari jalan ini.",
            icon="alert-triangle",
            color="#EF4444" if payload.estimated_depth_cm >= 40 else "#F59E0B",
            for_you=True,
            action_text="Lihat Rute Alternatif",
            action_route_id="route-safe"
        )
        db.add(alert)
        db.flush()
        alert_id = alert.id

    db.commit()

    return AIPredictionResponse(
        status="success",
        message=f"Prediksi AI untuk {payload.location_name} berhasil disimpan ke database geospasial",
        flood_point_id=point_id,
        alert_id=alert_id,
        confidence=payload.confidence
    )

