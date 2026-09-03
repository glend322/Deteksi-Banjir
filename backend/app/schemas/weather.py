from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HourlyForecast(BaseModel):
    time: str
    temp: int
    icon: str
    condition: str

class WeatherResponse(BaseModel):
    city: str
    condition: str
    temp: int
    unit: str = "°C"
    humidity: int
    wind_speed: str
    forecast_hourly: List[HourlyForecast]

class AlertResponse(BaseModel):
    id: int
    slug: Optional[str] = None
    category: str
    title: str
    location: str
    subtext: str
    time_ago: Optional[str] = "Baru saja"
    icon: str
    color: str
    for_you: bool
    action_text: Optional[str] = None
    action_route_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class EmergencyContact(BaseModel):
    name: str
    number: str
    desc: str

class EducationGuide(BaseModel):
    before: List[str]
    during: List[str]
    after: List[str]
    vehicle_thresholds: List[dict]

