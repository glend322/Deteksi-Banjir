from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from typing import List, Optional
import os
import shutil
import uuid

from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.api.endpoints.auth import get_current_user
from app.models.report import FloodReport
from app.models.flood import FloodPoint
from app.models.user import User
from app.schemas.report import FloodReportResponse, ReportConfirmResponse
from app.services.ai_service import process_ai_verification, confirm_report_by_peer

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Validasi upload foto (P1.5)
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


# ─────────────────────────────────────────────
# POST /reports  — Kirim Laporan Banjir Baru
# ─────────────────────────────────────────────
@router.post("", response_model=FloodReportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def submit_flood_report(
    request: Request,
    background_tasks: BackgroundTasks,
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
            # Validasi MIME type
            if photo.content_type not in ALLOWED_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Format file tidak didukung ({photo.content_type}). Gunakan JPEG, PNG, atau WebP."
                )

            # Validasi ukuran file
            content = await photo.read()
            if len(content) > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Ukuran file terlalu besar. Maksimum 5 MB."
                )

            ext = os.path.splitext(photo.filename)[1] or ".jpg"
            unique_name = f"report_{uuid.uuid4().hex[:10]}{ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            with open(file_path, "wb") as buffer:
                buffer.write(content)

            photo_url = f"/uploads/{unique_name}"

        # Validasi user_id jika ada
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
            is_verified=False,
            verification_status="pending",
            verification_note="Sedang diproses oleh pipeline AI & analisis cuaca...",
            ai_confidence=60,
            confirmations_count=1,
            geom=geom
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Jalankan verifikasi AI di background
        background_tasks.add_task(process_ai_verification, report.id, db)

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
            verification_status=report.verification_status,
            verification_note=report.verification_note,
            ai_confidence=report.ai_confidence,
            confirmations_count=report.confirmations_count,
            lat=lat,
            lng=lng,
            created_at=report.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Gagal memproses laporan: {str(e)}")


# ─────────────────────────────────────────────
# GET /reports  — Daftar Laporan (dengan filter & pagination)
# ─────────────────────────────────────────────
@router.get("", response_model=List[FloodReportResponse])
def get_flood_reports(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter: pending, verified, unverified, flagged"),
    is_verified: Optional[bool] = Query(None, description="Filter laporan terverifikasi"),
    skip: int = Query(0, ge=0, description="Jumlah data yang dilewati (offset)"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah data yang dikembalikan"),
    db: Session = Depends(get_db)
):
    query = db.query(
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
        FloodReport.verification_status,
        FloodReport.verification_note,
        FloodReport.ai_confidence,
        FloodReport.confirmations_count,
        FloodReport.created_at,
        func.ST_Y(FloodReport.geom).label("lat"),
        func.ST_X(FloodReport.geom).label("lng")
    )

    if status_filter:
        query = query.filter(FloodReport.verification_status == status_filter)
    if is_verified is not None:
        query = query.filter(FloodReport.is_verified == is_verified)

    results = query.order_by(FloodReport.created_at.desc()).offset(skip).limit(limit).all()

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
            verification_status=r.verification_status or "pending",
            verification_note=r.verification_note,
            ai_confidence=r.ai_confidence or 0,
            confirmations_count=r.confirmations_count or 0,
            lat=r.lat,
            lng=r.lng,
            created_at=r.created_at
        )
        for r in results
    ]


# ─────────────────────────────────────────────
# GET /reports/nearby  — Laporan terdekat dari koordinat GPS (P2.2)
# ─────────────────────────────────────────────
@router.get("/nearby", response_model=List[FloodReportResponse])
def get_nearby_reports(
    lat: float = Query(..., ge=-90, le=90, description="Latitude posisi pengguna"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude posisi pengguna"),
    radius_km: float = Query(5.0, ge=0.1, le=50.0, description="Radius pencarian dalam km"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Mengambil laporan warga dalam radius GPS tertentu menggunakan PostGIS ST_DWithin.
    Berguna untuk menampilkan laporan di sekitar posisi user di peta (PRD 6.2).
    """
    user_geom = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    radius_deg = radius_km / 111.0  # Konversi km ke derajat (approx)

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
        FloodReport.verification_status,
        FloodReport.verification_note,
        FloodReport.ai_confidence,
        FloodReport.confirmations_count,
        FloodReport.created_at,
        func.ST_Y(FloodReport.geom).label("lat"),
        func.ST_X(FloodReport.geom).label("lng")
    ).filter(
        func.ST_DWithin(FloodReport.geom, user_geom, radius_deg)
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
            verification_status=r.verification_status or "pending",
            verification_note=r.verification_note,
            ai_confidence=r.ai_confidence or 0,
            confirmations_count=r.confirmations_count or 0,
            lat=r.lat,
            lng=r.lng,
            created_at=r.created_at
        )
        for r in results
    ]


# ─────────────────────────────────────────────
# GET /reports/{report_id}  — Detail laporan tunggal (P1.3)
# ─────────────────────────────────────────────
@router.get("/{report_id}", response_model=FloodReportResponse)
def get_report_by_id(report_id: int, db: Session = Depends(get_db)):
    """Mengambil detail satu laporan banjir berdasarkan ID."""
    result = db.query(
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
        FloodReport.verification_status,
        FloodReport.verification_note,
        FloodReport.ai_confidence,
        FloodReport.confirmations_count,
        FloodReport.created_at,
        func.ST_Y(FloodReport.geom).label("lat"),
        func.ST_X(FloodReport.geom).label("lng")
    ).filter(FloodReport.id == report_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    return FloodReportResponse(
        id=result.id,
        user_id=result.user_id,
        location_name=result.location_name,
        address=result.address,
        depth_category=result.depth_category,
        depth_cm=result.depth_cm,
        condition=result.condition,
        description=result.description,
        photo_url=result.photo_url,
        is_verified=result.is_verified,
        verification_status=result.verification_status or "pending",
        verification_note=result.verification_note,
        ai_confidence=result.ai_confidence or 0,
        confirmations_count=result.confirmations_count or 0,
        lat=result.lat,
        lng=result.lng,
        created_at=result.created_at
    )


# ─────────────────────────────────────────────
# POST /reports/{report_id}/confirm  — Konfirmasi Peer
# ─────────────────────────────────────────────
@router.post("/{report_id}/confirm", response_model=ReportConfirmResponse)
def confirm_flood_report(report_id: int, db: Session = Depends(get_db)):
    """
    Peer Verification: Warga lain di sekitar lokasi mengonfirmasi kebenaran genangan air.
    """
    result = confirm_report_by_peer(report_id, db)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Laporan tidak ditemukan"))

    return ReportConfirmResponse(
        message="Terima kasih! Konfirmasi Anda membantu memvalidasi peta banjir warga.",
        report_id=result["report_id"],
        confirmations_count=result["confirmations_count"],
        is_verified=result["is_verified"],
        status=result["verification_status"]
    )


# ─────────────────────────────────────────────
# DELETE /reports/{report_id}  — Hapus laporan (pemilik atau admin) (P1.3)
# ─────────────────────────────────────────────
@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Menghapus laporan banjir. Hanya user pemilik laporan atau admin yang diizinkan.
    Juga menghapus file foto dari server jika ada.
    """
    report = db.query(FloodReport).filter(FloodReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    # Hanya pemilik atau admin yang bisa hapus
    if report.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk menghapus laporan ini"
        )

    # Hapus file foto dari disk jika bukan asset default
    if report.photo_url and report.photo_url.startswith("/uploads/"):
        file_path = os.path.join(UPLOAD_DIR, os.path.basename(report.photo_url))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass  # Lanjutkan meski file gagal dihapus

    db.delete(report)
    db.commit()
    return {"message": "Laporan berhasil dihapus", "id": report_id}
