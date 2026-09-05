from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.api.endpoints.auth import get_current_user, build_user_profile
from app.models.user import User, SavedLocation, TripHistory
from app.models.flood import FloodPoint, EvacuationPoint
from app.schemas.user import (
    UserProfile,
    UserUpdate,
    SavedLocationCreate,
    SavedLocationResponse,
    TripHistoryCreate,
    TripHistoryResponse,
    ProximityCheckRequest,
    ProximityCheckResponse,
    ProximityFloodHazard,
    ProximityEvacuationInfo
)

router = APIRouter()

@router.get("/me", response_model=UserProfile)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return build_user_profile(current_user, db)

@router.put("/me", response_model=UserProfile)
def update_my_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.vehicle_type is not None:
        current_user.vehicle_type = payload.vehicle_type
    if payload.vehicle_max_depth_cm is not None:
        current_user.vehicle_max_depth_cm = payload.vehicle_max_depth_cm
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    db.commit()
    db.refresh(current_user)
    return build_user_profile(current_user, db)

# --- Saved Locations ---

@router.get("/saved-locations", response_model=List[SavedLocationResponse])
def get_saved_locations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results = db.query(
        SavedLocation.id,
        SavedLocation.user_id,
        SavedLocation.name,
        SavedLocation.address,
        SavedLocation.icon,
        SavedLocation.created_at,
        func.ST_Y(SavedLocation.geom).label("lat"),
        func.ST_X(SavedLocation.geom).label("lng")
    ).filter(SavedLocation.user_id == current_user.id).all()

    return [
        SavedLocationResponse(
            id=r.id,
            user_id=r.user_id,
            name=r.name,
            address=r.address,
            icon=r.icon,
            lat=r.lat,
            lng=r.lng,
            created_at=r.created_at
        )
        for r in results
    ]

@router.post("/saved-locations", response_model=SavedLocationResponse, status_code=status.HTTP_201_CREATED)
def add_saved_location(
    payload: SavedLocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    geom = from_shape(Point(payload.lng, payload.lat), srid=4326)
    loc = SavedLocation(
        user_id=current_user.id,
        name=payload.name,
        address=payload.address,
        icon=payload.icon,
        geom=geom
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)

    return SavedLocationResponse(
        id=loc.id,
        user_id=loc.user_id,
        name=loc.name,
        address=loc.address,
        icon=loc.icon,
        lat=payload.lat,
        lng=payload.lng,
        created_at=loc.created_at
    )

@router.delete("/saved-locations/{location_id}", status_code=status.HTTP_200_OK)
def delete_saved_location(
    location_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loc = db.query(SavedLocation).filter(
        SavedLocation.id == location_id,
        SavedLocation.user_id == current_user.id
    ).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Lokasi tersimpan tidak ditemukan")

    db.delete(loc)
    db.commit()
    return {"message": "Lokasi tersimpan berhasil dihapus", "id": location_id}

# --- Trip History ---

@router.get("/trips", response_model=List[TripHistoryResponse])
def get_user_trip_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mengambil riwayat perjalanan rute aman pengguna."""
    trips = db.query(TripHistory).filter(
        TripHistory.user_id == current_user.id
    ).order_by(TripHistory.created_at.desc()).limit(limit).all()
    return trips

@router.post("/trips", response_model=TripHistoryResponse, status_code=status.HTTP_201_CREATED)
def save_trip_history(
    payload: TripHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Menyimpan log rute perjalanan yang dipilih/dilalui pengguna."""
    trip = TripHistory(
        user_id=current_user.id,
        origin_name=payload.origin_name,
        destination_name=payload.destination_name,
        duration_str=payload.duration_str,
        distance_km=payload.distance_km,
        route_type=payload.route_type,
        status=payload.status
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip

@router.delete("/trips/{trip_id}", status_code=status.HTTP_200_OK)
def delete_trip_history_item(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Menghapus 1 entri riwayat perjalanan."""
    trip = db.query(TripHistory).filter(
        TripHistory.id == trip_id,
        TripHistory.user_id == current_user.id
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Riwayat perjalanan tidak ditemukan")

    db.delete(trip)
    db.commit()
    return {"message": "Riwayat perjalanan berhasil dihapus", "id": trip_id}

# --- Proximity Geo-Alerts (PRD Bab 6.2 & 7) ---

@router.post("/check-proximity", response_model=ProximityCheckResponse)
def check_user_proximity_hazard(
    payload: ProximityCheckRequest,
    db: Session = Depends(get_db)
):
    """
    PRD 6.2 & 7: Real-Time Proximity Risk Warning (GPS Tracking).
    Mendeteksi apakah posisi GPS user berada dalam radius bahaya (<500 meter)
    dari titik banjir, serta merekomendasikan instruksi evakuasi terdekat.
    """
    user_geom = func.ST_SetSRID(func.ST_MakePoint(payload.lng, payload.lat), 4326)

    # 1. Cari titik banjir terdekat yang berstatus bahaya/waspada
    fp_distance_m = func.ST_DistanceSphere(FloodPoint.geom, user_geom)
    nearest_hazard_record = db.query(
        FloodPoint.id,
        FloodPoint.name,
        FloodPoint.depth_cm,
        FloodPoint.status,
        FloodPoint.status_label,
        FloodPoint.recommendation,
        fp_distance_m.label("distance_m")
    ).filter(
        FloodPoint.status.in_(["watch", "flooded", "impassable"])
    ).order_by(fp_distance_m).first()

    # 2. Cari posko evakuasi terdekat
    evac_distance_m = func.ST_DistanceSphere(EvacuationPoint.geom, user_geom)
    nearest_evac_record = db.query(
        EvacuationPoint.id,
        EvacuationPoint.name,
        EvacuationPoint.capacity,
        EvacuationPoint.supplies,
        EvacuationPoint.contact,
        evac_distance_m.label("distance_m")
    ).order_by(evac_distance_m).first()

    nearest_evac_info = None
    if nearest_evac_record:
        nearest_evac_info = ProximityEvacuationInfo(
            name=nearest_evac_record.name,
            distance_meters=int(round(nearest_evac_record.distance_m)),
            capacity=nearest_evac_record.capacity,
            supplies=nearest_evac_record.supplies,
            contact=nearest_evac_record.contact
        )

    # 3. Evaluasi Tingkat Bahaya (Radius <= 500 meter)
    vehicle_tolerance = payload.vehicle_max_depth_cm or 30
    is_in_danger = False
    danger_level = "SAFE"
    nearest_hazard_info = None

    if nearest_hazard_record:
        dist_m = int(round(nearest_hazard_record.distance_m))
        
        if dist_m <= 600: # Dalam radius 600m
            nearest_hazard_info = ProximityFloodHazard(
                name=nearest_hazard_record.name,
                distance_meters=dist_m,
                depth_cm=nearest_hazard_record.depth_cm,
                status=nearest_hazard_record.status,
                status_label=nearest_hazard_record.status_label or nearest_hazard_record.status,
                recommendation=nearest_hazard_record.recommendation
            )

            if nearest_hazard_record.depth_cm > vehicle_tolerance or nearest_hazard_record.status == "impassable":
                is_in_danger = True
                danger_level = "CRITICAL"
                warning_message = (
                    f"📍 PERINGATAN BAHAYA: Anda berada {dist_m} meter dari titik {nearest_hazard_record.name} "
                    f"(Kedalaman air {nearest_hazard_record.depth_cm} cm). Jalur ini TIDAK BISA DILALUI kendaraan Anda!"
                )
                recommended_action = (
                    f"Jangan memaksakan melintas ke arah {nearest_hazard_record.name}. Segera putar balik atau "
                    f"berlindung di posko evakuasi terdekat ({nearest_evac_info.name if nearest_evac_info else 'Posko BPBD'} - "
                    f"{nearest_evac_info.distance_meters if nearest_evac_info else 'dekat'} meter dari Anda)."
                )
            elif nearest_hazard_record.status in ["flooded", "watch"] or nearest_hazard_record.depth_cm >= 15:
                is_in_danger = True
                danger_level = "WARNING"
                warning_message = (
                    f"⚠️ PERHATIAN: Anda berada {dist_m} meter di dekat titik {nearest_hazard_record.name} "
                    f"(Status: {nearest_hazard_record.status_label or 'Waspada Genangan'}, Kedalaman: {nearest_hazard_record.depth_cm} cm)."
                )
                recommended_action = (
                    f"Kurangi kecepatan, waspada genangan air, atau pilih jalur alternatif via SafeRoute. "
                    f"Posko terdekat: {nearest_evac_info.name if nearest_evac_info else 'Posko Terdekat'} "
                    f"({nearest_evac_info.distance_meters if nearest_evac_info else 'dekat'} meter)."
                )
            else:
                warning_message = f"Kondisi jalan di sekitar Anda relatif aman (Genangan ringan di {nearest_hazard_record.name}, {dist_m}m)."
                recommended_action = "Lanjutkan perjalanan dengan tetap memantau perkembangan peta banjir."

    if not is_in_danger:
        warning_message = "Posisi GPS Anda saat ini berada di zona aman bebas banjir."
        recommended_action = "Lanjutkan perjalanan Anda sesuai rute yang direkomendasikan."

    return ProximityCheckResponse(
        is_in_danger_zone=is_in_danger,
        danger_level=danger_level,
        warning_message=warning_message,
        recommended_action=recommended_action,
        nearest_hazard=nearest_hazard_info,
        nearest_evacuation=nearest_evac_info,
        timestamp=datetime.now(timezone.utc)
    )


