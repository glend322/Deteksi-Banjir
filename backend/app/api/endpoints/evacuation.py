from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import to_shape
from typing import List, Optional

from app.core.database import get_db
from app.models.flood import EvacuationPoint
from app.schemas.flood import EvacuationPointResponse

router = APIRouter()

@router.get("", response_model=List[EvacuationPointResponse])
def get_evacuation_points(db: Session = Depends(get_db)):
    results = db.query(
        EvacuationPoint.id,
        EvacuationPoint.slug,
        EvacuationPoint.name,
        EvacuationPoint.capacity,
        EvacuationPoint.supplies,
        EvacuationPoint.contact,
        EvacuationPoint.status,
        func.ST_Y(EvacuationPoint.geom).label("lat"),
        func.ST_X(EvacuationPoint.geom).label("lng")
    ).all()

    return [
        EvacuationPointResponse(
            id=r.id,
            slug=r.slug,
            name=r.name,
            capacity=r.capacity,
            supplies=r.supplies,
            contact=r.contact,
            status=r.status,
            lat=r.lat,
            lng=r.lng
        )
        for r in results
    ]

@router.get("/nearest", response_model=List[EvacuationPointResponse])
def get_nearest_evacuation_points(
    lat: float = Query(..., ge=-90, le=90, description="Latitude posisi pengguna"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude posisi pengguna"),
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Mencari titik posko evakuasi terdekat berdasarkan koordinat GPS pengguna
    menggunakan kalkulasi jarak spasial PostGIS (ST_Distance).
    """
    user_geom = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    
    # Hitung jarak dalam kilometer menggunakan PostGIS ST_DistanceSphere
    distance_km = func.ST_DistanceSphere(EvacuationPoint.geom, user_geom) / 1000.0

    results = db.query(
        EvacuationPoint.id,
        EvacuationPoint.slug,
        EvacuationPoint.name,
        EvacuationPoint.capacity,
        EvacuationPoint.supplies,
        EvacuationPoint.contact,
        EvacuationPoint.status,
        func.ST_Y(EvacuationPoint.geom).label("lat"),
        func.ST_X(EvacuationPoint.geom).label("lng"),
        distance_km.label("distance_km")
    ).order_by(distance_km).limit(limit).all()

    return [
        EvacuationPointResponse(
            id=r.id,
            slug=r.slug,
            name=r.name,
            capacity=r.capacity,
            supplies=r.supplies,
            contact=r.contact,
            status=r.status,
            lat=r.lat,
            lng=r.lng,
            distance_km=round(r.distance_km, 2)
        )
        for r in results
    ]

