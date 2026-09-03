from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Severity(str, Enum):
    normal = "normal"
    waspada = "waspada"
    tergenang = "tergenang"
    tidak_dapat_dilalui = "tidak_dapat_dilalui"


class VerificationStatus(str, Enum):
    verified = "verified"
    unverified = "unverified"
    flagged = "flagged"


# --- CV Classifier ---

class CVResult(BaseModel):
    flood_detected: bool
    severity: Severity
    depth_range: str = Field(..., example="40-70cm")
    depth_estimate_cm: float = Field(..., ge=0, le=300)
    confidence: float = Field(..., ge=0, le=1)
    bounding_boxes: List[List[float]] = []


# --- Predictive Model ---

class FloodPrediction(BaseModel):
    area_id: str
    lat: float
    lng: float
    flood_probability: float = Field(..., ge=0, le=1)
    predicted_depth_range: str
    time_window: str
    confidence: float = Field(..., ge=0, le=1)
    risk_level: Severity


class PredictRequest(BaseModel):
    area_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    time_window: str = "3h"


# --- Report Verification ---

class ReportInput(BaseModel):
    report_id: str
    lat: float
    lng: float
    timestamp: str
    description: str
    photo_path: Optional[str] = None


class VerificationResult(BaseModel):
    report_id: str
    verification_status: VerificationStatus
    confidence_score: float = Field(..., ge=0, le=1)
    flags: List[str] = []
    estimated_depth: Optional[str] = None


# --- Flood Zone (for map) ---

class FloodZone(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    depth: float
    status: Severity
    confidence: float
    last_updated: str
    source: str


class FloodZoneResponse(BaseModel):
    zones: List[FloodZone]
