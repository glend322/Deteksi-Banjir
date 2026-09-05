from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FloodReportCreate(BaseModel):
    location_name: str
    address: Optional[str] = None
    depth_category: Optional[str] = "20-40 cm"
    depth_cm: Optional[int] = 30
    condition: Optional[str] = "Tergenang"
    description: Optional[str] = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class FloodReportResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    location_name: str
    address: Optional[str] = None
    depth_category: str = "20-40 cm"
    depth_cm: int = 30
    condition: str = "Tergenang"
    description: Optional[str] = None
    photo_url: Optional[str] = None
    is_verified: bool = False
    verification_status: str = "pending"
    verification_note: Optional[str] = None
    ai_confidence: int = 0
    confirmations_count: int = 0
    lat: float
    lng: float
    created_at: datetime

    class Config:
        from_attributes = True

class ReportConfirmResponse(BaseModel):
    message: str
    report_id: int
    confirmations_count: int
    is_verified: bool
    status: str

