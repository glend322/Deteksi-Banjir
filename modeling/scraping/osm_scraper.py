"""
OpenStreetMap Scraper — Overpass API

Scrapes geospatial features for Semarang:
- Drainage networks (waterways, drains)
- Land use (residential, commercial, industrial, green, water)
- Road network
- Water bodies (rivers, canals, lakes)
"""
import json
import sys
import time
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from utils import RateLimiter, Cache, log, SEMARANG_BOUNDS

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Build bounding box string for Overpass: (south,west,north,east)
BBOX = (
    f"{SEMARANG_BOUNDS['lat_min']},"
    f"{SEMARANG_BOUNDS['lng_min']},"
    f"{SEMARANG_BOUNDS['lat_max']},"
    f"{SEMARANG_BOUNDS['lng_max']}"
)


def overpass_query(query: str, rate_limiter: RateLimiter, cache: Cache) -> dict | None:
    cache_key = f"overpass_{hash(query)}"
    cached = cache.get_raw(cache_key)
    if cached:
        return cached

    rate_limiter.wait()
    # Try multiple Overpass endpoints
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    for endpoint in endpoints:
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            cache.set_raw(cache_key, data)
            return data
        except Exception as e:
            print(f"  Overpass ({endpoint.split('//')[1].split('/')[0]}) failed: {e}")
            rate_limiter.wait()
    return None


def scrape_waterways(rate_limiter: RateLimiter, cache: Cache) -> pd.DataFrame:
    log("  Scraping waterways (rivers, canals, drains)...")
    query = f"""
    [out:json][timeout:90];
    (
      way["waterway"~"river|canal|drain|ditch"]({BBOX});
      relation["waterway"~"river|canal|drain|ditch"]({BBOX});
    );
    out center tags;
    """
    data = overpass_query(query, rate_limiter, cache)
    if not data:
        return pd.DataFrame()

    records = []
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        center = elem.get("center", {})
        records.append({
            "osm_id": elem.get("id"),
            "type": elem.get("type"),
            "waterway": tags.get("waterway"),
            "name": tags.get("name", ""),
            "width": tags.get("width"),
            "depth": tags.get("depth"),
            "lat": center.get("lat"),
            "lng": center.get("lon"),
        })
    df = pd.DataFrame(records)
    log(f"    Found {len(df)} waterways")
    return df


def scrape_land_use(rate_limiter: RateLimiter, cache: Cache) -> pd.DataFrame:
    log("  Scraping land use...")
    query = f"""
    [out:json][timeout:90];
    (
      way["landuse"]({BBOX});
      relation["landuse"]({BBOX});
    );
    out center tags;
    """
    data = overpass_query(query, rate_limiter, cache)
    if not data:
        return pd.DataFrame()

    records = []
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        center = elem.get("center", {})
        records.append({
            "osm_id": elem.get("id"),
            "type": elem.get("type"),
            "landuse": tags.get("landuse"),
            "name": tags.get("name", ""),
            "lat": center.get("lat"),
            "lng": center.get("lon"),
        })
    df = pd.DataFrame(records)
    log(f"    Found {len(df)} land use areas")
    return df


def scrape_water_bodies(rate_limiter: RateLimiter, cache: Cache) -> pd.DataFrame:
    log("  Scraping water bodies...")
    query = f"""
    [out:json][timeout:90];
    (
      way["natural"="water"]({BBOX});
      relation["natural"="water"]({BBOX});
      way["waterway"="riverbank"]({BBOX});
    );
    out center tags;
    """
    data = overpass_query(query, rate_limiter, cache)
    if not data:
        return pd.DataFrame()

    records = []
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        center = elem.get("center", {})
        records.append({
            "osm_id": elem.get("id"),
            "type": elem.get("type"),
            "water_type": tags.get("water", tags.get("waterway", "unknown")),
            "name": tags.get("name", ""),
            "lat": center.get("lat"),
            "lng": center.get("lon"),
        })
    df = pd.DataFrame(records)
    log(f"    Found {len(df)} water bodies")
    return df


def scrape_roads(rate_limiter: RateLimiter, cache: Cache) -> pd.DataFrame:
    log("  Scraping road network...")
    query = f"""
    [out:json][timeout:90];
    (
      way["highway"~"motorway|trunk|primary|secondary|tertiary|residential"]({BBOX});
    );
    out tags;
    """
    data = overpass_query(query, rate_limiter, cache)
    if not data:
        return pd.DataFrame()

    records = []
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        records.append({
            "osm_id": elem.get("id"),
            "highway": tags.get("highway"),
            "name": tags.get("name", ""),
            "lanes": tags.get("lanes"),
            "surface": tags.get("surface"),
            "bridge": tags.get("bridge"),
            "tunnel": tags.get("tunnel"),
        })
    df = pd.DataFrame(records)
    log(f"    Found {len(df)} roads")
    return df


def scrape_flood_prone_features(rate_limiter: RateLimiter, cache: Cache) -> pd.DataFrame:
    log("  Scraping flood-related features...")
    query = f"""
    [out:json][timeout:90];
    (
      way["natural"="wetland"]({BBOX});
      way["landuse"="reservoir"]({BBOX});
      way["man_made"="storm_drain"]({BBOX});
      way["waterway"="drain"]({BBOX});
      node["man_made"="monitoring_station"]({BBOX});
    );
    out center tags;
    """
    data = overpass_query(query, rate_limiter, cache)
    if not data:
        return pd.DataFrame()

    records = []
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        center = elem.get("center", elem)
        records.append({
            "osm_id": elem.get("id"),
            "type": elem.get("type"),
            "feature": tags.get("waterway", tags.get("natural", tags.get("man_made", "unknown"))),
            "name": tags.get("name", ""),
            "lat": center.get("lat", center.get("lat")),
            "lng": center.get("lon", center.get("lon")),
        })
    df = pd.DataFrame(records)
    log(f"    Found {len(df)} flood-prone features")
    return df


def main():
    output_dir = Path(__file__).parent.parent / "data" / "raw" / "osm"
    output_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = Path(__file__).parent.parent / "data" / "raw" / "_cache"
    cache = Cache(str(cache_dir))
    rate_limiter = RateLimiter(min_interval=2.0)  # Overpass needs slower rate

    log("Scraping OpenStreetMap data for Semarang...")

    waterways = scrape_waterways(rate_limiter, cache)
    land_use = scrape_land_use(rate_limiter, cache)
    water_bodies = scrape_water_bodies(rate_limiter, cache)
    roads = scrape_roads(rate_limiter, cache)
    flood_features = scrape_flood_prone_features(rate_limiter, cache)

    # Save individual datasets
    if not waterways.empty:
        waterways.to_csv(output_dir / "waterways.csv", index=False)
    if not land_use.empty:
        land_use.to_csv(output_dir / "land_use.csv", index=False)
    if not water_bodies.empty:
        water_bodies.to_csv(output_dir / "water_bodies.csv", index=False)
    if not roads.empty:
        roads.to_csv(output_dir / "roads.csv", index=False)
    if not flood_features.empty:
        flood_features.to_csv(output_dir / "flood_features.csv", index=False)

    # Create summary
    summary = {
        "area": "Kota Semarang",
        "bounds": SEMARANG_BOUNDS,
        "waterways_count": len(waterways),
        "land_use_count": len(land_use),
        "water_bodies_count": len(water_bodies),
        "roads_count": len(roads),
        "flood_features_count": len(flood_features),
    }
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log("OSM scraping complete!")
    print(f"\n--- Summary ---")
    for k, v in summary.items():
        if k != "bounds":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
