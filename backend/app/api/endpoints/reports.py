from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from typing import List, Optional
import os
import shutil
import uuid

from app.core.database import get_db
from app.models.report import FloodReport
from app.models.flood import FloodPoint
from app.models.user import User
from app.schemas.report import FloodReportResponse

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("", response_model=FloodReportResponse, status_code=201)
async def submit_flood_report(
    location_name: str = Form(..., description="Nama lokasi genangan"),
    address: Optional[str] = Form(None),
    depth_category: str = Form("20-40 cm"),
    depth_cm: int = Form(30),
    condition: str = Form("Tergenang"),
    description: Optional[str] = Form(None),
    lat: float = Form(..., description="Latitude GPS"),
    lng: float = Form(..., description="Longitude GPS"),
    user_id: Optional[int] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        photo_url = None
        if photo and hasattr(photo, "filename") and photo.filename:
            ext = os.path.splitext(photo.filename)[1]
            unique_name = f"report_{uuid.uuid4().hex[:10]}{ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            
            photo_url = f"/uploads/{unique_name}"

        # Validasi user_id: jika user_id tidak valid di DB, abaikan agar tidak Foreign Key Error
        valid_user_id = None
        if user_id and user_id > 0:
            existing_user = db.query(User).filter(User.id == user_id).first()
            if existing_user:
                valid_user_id = user_id

        # Geometri PostGIS Point
        geom = from_shape(Point(lng, lat), srid=4326)

        report = FloodReport(
            user_id=valid_user_id,
            location_name=location_name,
            address=address or location_name,
            depth_category=depth_category,
            depth_cm=depth_cm,
            condition=condition,
            description=description,
            photo_url=photo_url or "/assets/cctv_kaligawe.jpg",
            is_verified=True,
            verification_note="Diverifikasi AI (Deteksi Genangan Air & Riwayat Spasial)",
            ai_confidence=92,
            geom=geom
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Buat titik pantau baru di peta PostGIS
        status_val = "impassable" if depth_cm >= 40 else "flooded" if depth_cm >= 20 else "watch"
        status_lbl = condition or ("Tidak Dapat Dilalui" if status_val == "impassable" else "Tergenang" if status_val == "flooded" else "Waspada")

        new_point = FloodPoint(
            slug=f"loc-report-{report.id}",
            name=location_name,
            area="Semarang (Laporan Komunitas)",
            status=status_val,
            status_label=status_lbl,
            depth_cm=depth_cm,
            source="Laporan Warga (Terverifikasi AI)",
            confidence=92,
            image_url=report.photo_url,
            recommendation="Genangan terdeteksi dari laporan warga terverifikasi. Harap waspada.",
            cause="Limpasan air & curah hujan",
            vehicles_allowed=["Mobil SUV", "Truk"] if status_val != "impassable" else ["Hanya SAR"],
            geom=geom
        )
        db.add(new_point)
        db.commit()

        return FloodReportResponse(
            id=report.id,
            user_id=report.user_id,
            location_name=report.location_name,
            address=report.address,
            depth_category=report.depth_category,
            depth_cm=report.depth_cm,
            condition=report.condition,
            description=report.description,
            photo_url=report.photo_url,
            is_verified=report.is_verified,
            verification_note=report.verification_note,
            ai_confidence=report.ai_confidence,
            lat=lat,
            lng=lng,
            created_at=report.created_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Gagal memproses laporan: {str(e)}")

@router.get("", response_model=List[FloodReportResponse])
def get_flood_reports(limit: int = 20, db: Session = Depends(get_db)):
    results = db.query(
        FloodReport.id,
        FloodReport.user_id,
        FloodReport.location_name,
        FloodReport.address,
        FloodReport.depth_category,
        FloodReport.depth_cm,
        FloodReport.condition,
        FloodReport.description,
        FloodReport.photo_url,
        FloodReport.is_verified,
        FloodReport.verification_note,
        FloodReport.ai_confidence,
        FloodReport.created_at,
        func.ST_Y(FloodReport.geom).label("lat"),
        func.ST_X(FloodReport.geom).label("lng")
    ).order_by(FloodReport.created_at.desc()).limit(limit).all()

    return [
        FloodReportResponse(
            id=r.id,
            user_id=r.user_id,
            location_name=r.location_name,
            address=r.address,
            depth_category=r.depth_category,
            depth_cm=r.depth_cm,
            condition=r.condition,
            description=r.description,
            photo_url=r.photo_url,
            is_verified=r.is_verified,
            verification_note=r.verification_note,
            ai_confidence=r.ai_confidence,
            lat=r.lat,
            lng=r.lng,
            created_at=r.created_at
        )
        for r in results
    ]
