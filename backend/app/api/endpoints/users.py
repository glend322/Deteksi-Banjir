from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from typing import List

from app.core.database import get_db
from app.api.endpoints.auth import get_current_user, build_user_profile
from app.models.user import User, SavedLocation, TripHistory
from app.schemas.user import UserProfile, UserUpdate, SavedLocationCreate, SavedLocationResponse

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

@router.post("/saved-locations", response_model=SavedLocationResponse, status_code=201)
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

