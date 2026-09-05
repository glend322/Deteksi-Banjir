import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.flood import FloodPoint, EvacuationPoint
from app.schemas.user import ProximityCheckRequest
from app.api.endpoints.users import check_user_proximity_hazard

def debug_proximity():
    db = SessionLocal()
    try:
        print("--- Querying all flood points in DB ---")
        points = db.query(FloodPoint).all()
        print(f"Total flood points in DB: {len(points)}")
        for p in points:
            print(f"ID: {p.id} | Slug: {p.slug} | Name: {p.name} | Status: {p.status} | Depth: {p.depth_cm}cm")

        req = ProximityCheckRequest(
            lat=-6.9540,
            lng=110.4560,
            vehicle_max_depth_cm=20
        )
        res = check_user_proximity_hazard(req, db)
        print("\n--- check_user_proximity_hazard Result ---")
        print("is_in_danger_zone:", res.is_in_danger_zone)
        print("danger_level:", res.danger_level)
        print("warning_message:", res.warning_message)
        print("recommended_action:", res.recommended_action)
        if res.nearest_hazard:
            print("nearest_hazard:", res.nearest_hazard.name, res.nearest_hazard.distance_meters, "m")
        if res.nearest_evacuation:
            print("nearest_evacuation:", res.nearest_evacuation.name, res.nearest_evacuation.distance_meters, "m")
    finally:
        db.close()

if __name__ == "__main__":
    debug_proximity()

