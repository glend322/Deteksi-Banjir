"""
FastAPI Schemas — Pydantic Models

Matches output contract from js/data.js (SAFEROUTE_DATA).
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class FloodStatus(str, Enum):
    safe = "safe"
    watch = "watch"
    flooded = "flooded"
    impassable = "impassable"


class Classification(str, Enum):
    dangkal = "dangkal"
    sedang = "sedang"
    dalam = "dalam"


# --- CV Classifier ---

class CVResult(BaseModel):
    flood_detected: bool
    classification: str = Field(..., example="dangkal")
    depth_label: str = Field(..., example="sedang")
    confidence: float = Field(..., ge=0, le=1)


# --- CCTV Scan ---

class CCTVScanRequest(BaseModel):
    categories: Optional[List[str]] = None
    camera_ids: Optional[List[int]] = None


class CCTVFrameResult(BaseModel):
    camera_id: int
    camera_name: str
    lat: float
    lng: float
    stream_url: str
    flood_detected: bool
    classification: str
    depth_label: str
    confidence: float
    area_name: str
    notification: str
    status: str
    status_label: str
    color: str
    false_positive_filtered: bool
    filter_reasons: List[str] = []
    frame_timestamp: float


class CCTVScanResponse(BaseModel):
    timestamp: float
    total_cameras: int
    scanned_cameras: int
    successful_frames: int
    failed_frames: int
    detections: List[CCTVFrameResult]


# --- Route Calculation ---

class Coordinate(BaseModel):
    lat: float
    lng: float
    name: Optional[str] = None


class RouteCalculateRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    vehicle_max_depth: Optional[str] = "sedang"


class RoadLabel(BaseModel):
    segment: str
    status: str
    color: str
    depth_label: str = "dangkal"


class RouteOption(BaseModel):
    id: str
    type: str
    title: str
    badge: str
    duration: str
    distance: str
    flood_avoided: str
    risk_level: str
    color: str
    description: str
    path: List[List[float]]
    road_labels: List[RoadLabel] = []


class EvacuationResult(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    distance_km: float
    duration_walk: str
    capacity: str
    contact: str
    status: str


class RouteCalculateResponse(BaseModel):
    origin: str
    destination: str
    flood_zones_active: int
    options: List[RouteOption]
    nearest_evacuation: Optional[EvacuationResult] = None


# --- Flood Zone ---

class FloodZone(BaseModel):
    id: str
    name: str
    area: str
    lat: float
    lng: float
    status: FloodStatus
    status_label: str
    depth_label: str
    confidence: float
    source: str
    classification: str = ""
    notification: str = ""
    last_updated: str
    color: str


class FloodZoneResponse(BaseModel):
    zones: List[FloodZone]
