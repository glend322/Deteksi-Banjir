from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = "Warga Semarang"
    vehicle_type: Optional[str] = "Mobil (City Car)"
    vehicle_max_depth_cm: Optional[int] = 30

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserProfile"

class SavedLocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    icon: Optional[str] = "map-pin"
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class SavedLocationCreate(SavedLocationBase):
    pass

class SavedLocationResponse(SavedLocationBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    avatar_url: Optional[str]
    vehicle_type: str
    vehicle_max_depth_cm: int
    trust_score: int = 50
    total_reports: int = 0
    verified_reports: int = 0
    saved_locations: List[SavedLocationResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_max_depth_cm: Optional[int] = None
    avatar_url: Optional[str] = None

# --- Trip History Schemas ---

class TripHistoryBase(BaseModel):
    origin_name: str
    destination_name: str
    duration_str: Optional[str] = "30 menit"
    distance_km: Optional[float] = 10.0
    route_type: Optional[str] = "Rute Teraman"
    status: Optional[str] = "Berhasil Menghindar Banjir"

class TripHistoryCreate(TripHistoryBase):
    pass

class TripHistoryResponse(TripHistoryBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Proximity Geo-Alert Schemas ---

class ProximityCheckRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude posisi pengguna saat ini")
    lng: float = Field(..., ge=-180, le=180, description="Longitude posisi pengguna saat ini")
    vehicle_max_depth_cm: Optional[int] = 30

class ProximityFloodHazard(BaseModel):
    name: str
    distance_meters: int
    depth_cm: int
    status: str
    status_label: str
    recommendation: Optional[str] = None

class ProximityEvacuationInfo(BaseModel):
    name: str
    distance_meters: int
    capacity: Optional[str] = None
    supplies: Optional[str] = None
    contact: Optional[str] = None

class ProximityCheckResponse(BaseModel):
    is_in_danger_zone: bool
    danger_level: str # SAFE, WARNING, CRITICAL
    warning_message: str
    recommended_action: str
    nearest_hazard: Optional[ProximityFloodHazard] = None
    nearest_evacuation: Optional[ProximityEvacuationInfo] = None
    timestamp: datetime


