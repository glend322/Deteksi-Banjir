from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=True)
    category = Column(String(50), default="warning") # urgent, warning, info
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    subtext = Column(Text, nullable=False)
    icon = Column(String(50), default="alert-triangle")
    color = Column(String(20), default="#F59E0B")
    for_you = Column(Boolean, default=True)
    action_text = Column(String(100), nullable=True)
    action_route_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WeatherForecastCache(Base):
    __tablename__ = "weather_forecast_cache"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), default="Semarang")
    condition = Column(String(100), default="Hujan Ringan")
    temp = Column(Integer, default=27)
    humidity = Column(Integer, default=86)
    wind_speed = Column(String(50), default="14 km/jam")
    forecast_hourly = Column(JSON, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

