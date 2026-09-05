from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FloodPointBase(BaseModel):
    name: str
    area: str
    status: str # safe, watch, flooded, impassable
    status_label: Optional[str] = None
    depth_cm: int = 0
    confidence: int = 100
    source: str = "CCTV Dinas PU"
    image_url: Optional[str] = None
    recommendation: Optional[str] = None
    cause: Optional[str] = None
    vehicles_allowed: Optional[List[str]] = []
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class FloodPointCreate(FloodPointBase):
    slug: Optional[str] = None

class FloodPointResponse(FloodPointBase):
    id: int
    slug: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FloodZoneResponse(BaseModel):
    id: int
    slug: Optional[str] = None
    name: str
    status: str
    fill_color: str
    fill_opacity: float
    border_color: str
    border_weight: int
    coordinates: List[List[float]] # List of [lat, lng] pairs

    class Config:
        from_attributes = True

class EvacuationPointResponse(BaseModel):
    id: int
    slug: Optional[str] = None
    name: str
    capacity: Optional[str] = None
    supplies: Optional[str] = None
    contact: Optional[str] = None
    status: str
    lat: float
    lng: float
    distance_km: Optional[float] = None # Calculated dynamically in proximity search

    class Config:
        from_attributes = True

class RiskSummaryItem(BaseModel):
    count: int
    label: str
    color: str
    desc: str

class RiskSummaryResponse(BaseModel):
    safe: RiskSummaryItem
    watch: RiskSummaryItem
    flooded: RiskSummaryItem
    impassable: RiskSummaryItem

class EnvironmentalRiskBase(BaseModel):
    name: str
    category: str # polder_pump, river_waste, drainage_choke, coastal_tide
    category_label: Optional[str] = None
    risk_level: str = "medium" # optimal, low, medium, high
    status: str
    capacity_or_condition: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = "pump"
    color: Optional[str] = "#10B981"
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class EnvironmentalRiskCreate(EnvironmentalRiskBase):
    slug: Optional[str] = None

class EnvironmentalRiskResponse(EnvironmentalRiskBase):
    id: int
    slug: Optional[str] = None
    distance_km: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EnvironmentalCategorySummary(BaseModel):
    category: str
    label: str
    total_count: int
    critical_count: int
    optimal_count: int

class EnvironmentalRiskSummaryResponse(BaseModel):
    total_points: int
    active_pumps: int
    critical_drainage_chokes: int
    river_waste_hotspots: int
    coastal_tide_risks: int
    categories: List[EnvironmentalCategorySummary]

