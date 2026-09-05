from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.routes import RouteCalculateRequest, RouteCalculateResponse
from app.services.routing_service import calculate_safe_routes as calculate_dynamic_safe_routes

router = APIRouter()

@router.post("/calculate", response_model=RouteCalculateResponse)
async def calculate_safe_routes(payload: RouteCalculateRequest, db: Session = Depends(get_db)):
    """
    Kalkulasi rute cerdas secara dinamis berbasis Open Source Routing Machine (OSRM)
    dan analisa spasial PostGIS untuk menghindari titik & zona genangan banjir.
    """
    vehicle_type = payload.vehicle_type or "Mobil (City Car)"
    vehicle_max_depth_cm = payload.vehicle_max_depth_cm or 30

    response = await calculate_dynamic_safe_routes(
        origin=payload.origin,
        destination=payload.destination,
        vehicle_type=vehicle_type,
        vehicle_max_depth_cm=vehicle_max_depth_cm,
        db=db
    )
    return response


