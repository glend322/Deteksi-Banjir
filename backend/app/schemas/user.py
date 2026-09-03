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
    saved_locations: List[SavedLocationResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_max_depth_cm: Optional[int] = None
    avatar_url: Optional[str] = None

