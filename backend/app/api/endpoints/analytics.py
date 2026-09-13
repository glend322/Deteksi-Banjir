from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.database import get_db
from app.models.flood import FloodPoint
from app.models.report import FloodReport
from app.models.user import User

router = APIRouter()


@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    Ringkasan metrik sistem SafeRoute Semarang (PRD Bab 10).
    Berguna untuk dashboard admin dan laporan keberhasilan hackathon.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Laporan hari ini
    total_reports_today = db.query(FloodReport).filter(
        FloodReport.created_at >= today_start
    ).count()

    verified_reports_today = db.query(FloodReport).filter(
        FloodReport.created_at >= today_start,
        FloodReport.is_verified == True
    ).count()

    # Titik banjir aktif
    active_flood_points = db.query(FloodPoint).filter(
        FloodPoint.status.in_(["watch", "flooded", "impassable"])
    ).count()

    impassable_count = db.query(FloodPoint).filter(
        FloodPoint.status == "impassable"
    ).count()

    # Confidence rata-rata semua laporan terverifikasi
    avg_confidence_result = db.query(func.avg(FloodReport.ai_confidence)).filter(
        FloodReport.is_verified == True
    ).scalar()
    avg_confidence = round(float(avg_confidence_result), 1) if avg_confidence_result else 0.0

    # Area yang paling banyak dilaporkan
    most_reported = db.query(
        FloodReport.location_name,
        func.count(FloodReport.id).label("count")
    ).group_by(FloodReport.location_name).order_by(
        func.count(FloodReport.id).desc()
    ).first()

    # Total pengguna terdaftar
    total_users = db.query(User).count()

    # Laporan pending (belum diverifikasi)
    pending_reports = db.query(FloodReport).filter(
        FloodReport.verification_status == "pending"
    ).count()

    # Risk summary
    safe_cnt = db.query(FloodPoint).filter(FloodPoint.status == "safe").count()
    watch_cnt = db.query(FloodPoint).filter(FloodPoint.status == "watch").count()
    flooded_cnt = db.query(FloodPoint).filter(FloodPoint.status == "flooded").count()

    return {
        "generated_at": now.isoformat(),
        "reports": {
            "total_today": total_reports_today,
            "verified_today": verified_reports_today,
            "pending": pending_reports,
            "verification_rate_today": (
                round(verified_reports_today / total_reports_today * 100, 1)
                if total_reports_today > 0 else 0.0
            ),
        },
        "flood_status": {
            "active_flood_points": active_flood_points,
            "impassable": impassable_count,
            "flooded": flooded_cnt,
            "watch": watch_cnt,
            "safe": safe_cnt,
        },
        "ai_metrics": {
            "avg_ai_confidence": avg_confidence,
            "most_reported_location": most_reported.location_name if most_reported else "-",
            "most_reported_count": most_reported.count if most_reported else 0,
        },
        "users": {
            "total_registered": total_users,
        },
    }

