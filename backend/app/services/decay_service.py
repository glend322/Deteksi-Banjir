import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.flood import FloodPoint

logger = logging.getLogger(__name__)

def apply_confidence_decay(db: Session) -> dict:
    """
    Mengimplementasikan PRD 5.5: Freshness & Confidence Data Decay
    - Mengurangi skor confidence secara bertahap jika tidak ada pembaruan laporan baru (-5% per jam).
    - Memulihkan status titik genangan menjadi 'safe' (surut) jika sudah lewat > 6 jam dan confidence < 25%.
    """
    now = datetime.now(timezone.utc)
    points = db.query(FloodPoint).filter(FloodPoint.status.in_(["watch", "flooded", "impassable"])).all()
    decayed_count = 0
    receded_count = 0

    for point in points:
        if not point.updated_at:
            continue
            
        updated_time = point.updated_at
        if updated_time.tzinfo is None:
            updated_time = updated_time.replace(tzinfo=timezone.utc)
            
        diff_hours = (now - updated_time).total_seconds() / 3600.0
        
        if diff_hours >= 1.0:
            penalty = int(diff_hours * 5)
            new_confidence = max(10, point.confidence - penalty)
            if new_confidence != point.confidence:
                point.confidence = new_confidence
                decayed_count += 1

            # Auto-clear jika genangan sudah lama dan tidak ada update baru (> 6 jam & confidence <= 25%)
            if diff_hours >= 6.0 and new_confidence <= 25 and point.status != "safe":
                point.status = "safe"
                point.status_label = "Aman (Genangan Telah Surut)"
                point.depth_cm = 0
                point.confidence = 90
                point.recommendation = "Genangan air telah surut total. Jalur aman dilalui semua jenis kendaraan."
                point.cause = "Kondisi air surut normal"
                receded_count += 1

    if decayed_count > 0 or receded_count > 0:
        db.commit()
        logger.info(f"⏳ Data Freshness: {decayed_count} titik mengalami decay, {receded_count} titik dinormalkan (surut).")

    return {
        "decayed_count": decayed_count,
        "receded_count": receded_count,
        "total_active_points_checked": len(points)
    }


