import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.flood import FloodPoint

logger = logging.getLogger(__name__)

def apply_confidence_decay(db: Session) -> int:
    """
    Mengimplementasikan PRD 5.5: Freshness & Confidence Data Decay
    """
    now = datetime.now(timezone.utc)
    points = db.query(FloodPoint).filter(FloodPoint.status.in_(["watch", "flooded", "impassable"])).all()
    updated_count = 0

    for point in points:
        if not point.updated_at:
            continue
            
        updated_time = point.updated_at
        if updated_time.tzinfo is None:
            updated_time = updated_time.replace(tzinfo=timezone.utc)
            
        diff_hours = (now - updated_time).total_seconds() / 3600.0
        
        if diff_hours >= 1.0:
            penalty = int(diff_hours * 5)
            new_confidence = max(15, point.confidence - penalty)
            if new_confidence != point.confidence:
                point.confidence = new_confidence
                updated_count += 1

    if updated_count > 0:
        db.commit()
        logger.info(f"⏳ Confidence decay diaplikasikan pada {updated_count} titik banjir.")

    return updated_count

