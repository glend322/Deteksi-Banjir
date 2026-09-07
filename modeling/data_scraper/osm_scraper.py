"""
OSM Scraper — OpenStreetMap Features via Overpass API

Downloads road networks, drainage, waterways, and land use for Semarang.
"""
import json
import logging
from typing import Optional

from utils import fetch_with_retry, RateLimiter

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

rate_limiter = RateLimiter(requests_per_second=0.5)

SEMARANG_BBOX = "-7.10,110.30,-6.90,110.55"


async def fetch_roads(bbox: str = SEMARANG_BBOX) -> Optional[dict]:
    query = f"""
    [out:json][timeout:60];
    (
      way["highway"~"primary|secondary|tertiary|residential"]({bbox});
    );
    out body;
    >;
    out skel;
    """
    return await _run_query(query, "roads")


async def fetch_waterways(bbox: str = SEMARANG_BBOX) -> Optional[dict]:
    query = f"""
    [out:json][timeout:60];
    (
      way["waterway"~"river|stream|drain|canal"]({bbox});
    );
    out body;
    >;
    out skel;
    """
    return await _run_query(query, "waterways")


async def fetch_drainage(bbox: str = SEMARANG_BBOX) -> Optional[dict]:
    query = f"""
    [out:json][timeout:60];
    (
      way["waterway"~"drain"]({bbox});
      way["man_made"~"storm_drain"]({bbox});
    );
    out body;
    >;
    out skel;
    """
    return await _run_query(query, "drainage")


async def fetch_land_use(bbox: str = SEMARANG_BBOX) -> Optional[dict]:
    query = f"""
    [out:json][timeout:60];
    (
      way["landuse"]({bbox});
    );
    out body;
    >;
    out skel;
    """
    return await _run_query(query, "land_use")


async def _run_query(query: str, name: str) -> Optional[dict]:
    rate_limiter.wait()

    try:
        import httpx
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[OSM] Fetched {name}: {len(data.get('elements', []))} elements")
            return data
    except Exception as e:
        logger.error(f"[OSM] Failed to fetch {name}: {e}")
        return None
