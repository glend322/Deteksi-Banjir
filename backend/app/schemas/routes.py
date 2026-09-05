from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class RouteLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    name: Optional[str] = None

class RouteCalculateRequest(BaseModel):
    origin: RouteLocation
    destination: RouteLocation
    vehicle_type: Optional[str] = "Mobil (City Car)"
    vehicle_max_depth_cm: Optional[int] = 30

class RouteOption(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str # route-safe, route-fastest, route-alternative
    type: str # safe, fastest, alternative
    title: str
    badge: str
    duration: str
    distance: str
    flood_avoided: str = Field(..., alias="floodAvoided")
    risk_level: str = Field(..., alias="riskLevel")
    color: str
    description: str
    path: List[List[float]] # [[lat, lng], [lat, lng], ...]
    max_depth_cm: Optional[int] = 0
    flood_points_intersected: Optional[List[str]] = []
    is_vehicle_safe: Optional[bool] = True

class RouteCalculateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    origin: str
    destination: str
    options: List[RouteOption]
    engine: Optional[str] = "OSRM + PostGIS Spatial Avoidance"


