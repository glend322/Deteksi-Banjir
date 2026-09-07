"""
BMKG Scraper — Curah Hujan Real-time & Historis

Scrapes rainfall data from BMKG for Semarang area.
Source: cuaca.bmkg.go.id
"""
import json
import logging
from pathlib import Path
from typing import Optional

from utils import fetch_with_retry, RateLimiter

logger = logging.getLogger(__name__)

BMKG_API_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
BMKG_AREA_ID = "501210"  # Semarang

rate_limiter = RateLimiter(requests_per_second=0.5)


async def fetch_current_weather(area_id: str = BMKG_AREA_ID) -> Optional[dict]:
    rate_limiter.wait()

    url = f"{BMKG_API_URL}?area={area_id}"
    content = await fetch_with_retry(url, timeout=15.0)

    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error("[BMKG] Failed to parse JSON response")
            return None

    return None


async def fetch_rainfall_forecast(area_id: str = BMKG_AREA_ID) -> list[dict]:
    data = await fetch_current_weather(area_id)
    if not data:
        return []

    forecasts = []
    try:
        for item in data.get("data", []):
            for cuaca in item.get("cuaca", []):
                for jam_data in cuaca:
                    hour = jam_data.get("jamCuaca", "")
                    rainfall = jam_data.get("curahHujan", {}).get("value", 0)
                    forecasts.append({
                        "time": hour,
                        "rainfall_mm": float(rainfall),
                    })
    except (KeyError, TypeError) as e:
        logger.error(f"[BMKG] Parse error: {e}")

    return forecasts


async def fetch_historical_rainfall(
    lat: float = -6.97,
    lng: float = 110.42,
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
) -> list[dict]:
    logger.info(f"[BMKG] Historical rainfall for {lat},{lng} from {start_date} to {end_date}")
    logger.info("[BMKG] Using fallback/sample data for historical rainfall")

    return []
