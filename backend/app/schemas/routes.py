from pydantic import BaseModel, Field
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
    id: str # route-safe, route-fastest, route-alternative
    type: str # safe, fastest, alternative
    title: str
    badge: str
    duration: str
    distance: str
    flood_avoided: str
    risk_level: str
    color: str
    description: str
    path: List[List[float]] # [[lat, lng], [lat, lng], ...]

class RouteCalculateResponse(BaseModel):
    origin: str
    destination: str
    options: List[RouteOption]

