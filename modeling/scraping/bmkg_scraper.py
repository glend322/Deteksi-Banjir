"""
BMKG Rainfall Scraper — via Open-Meteo (free, no API key)

Open-Meteo provides historical weather data for any GPS coordinate.
We use it to get hourly rainfall for Semarang areas.

Alternative: BMKG Data Online (requires account, last 2 years only)
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from utils import RateLimiter, Cache, log, SEMARANG_BOUNDS

# Open-Meteo free API (no key needed)
OPEN_METEO_HISTORICAL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"

# Key flood-prone areas in Semarang with coordinates
SEMARANG_AREAS = {
    "kaligawe": {"lat": -6.9420, "lng": 110.4200, "name": "Kaligawe"},
    "genuk": {"lat": -6.9550, "lng": 110.4450, "name": "Genuk"},
    "semarang_utara": {"lat": -6.9500, "lng": 110.4250, "name": "Semarang Utara"},
    "tambakrejo": {"lat": -6.9600, "lng": 110.4350, "name": "Tambakrejo"},
    "mangkang": {"lat": -6.9750, "lng": 110.3950, "name": "Mangkang"},
    "gayamsari": {"lat": -6.9700, "lng": 110.4450, "name": "Gayamsari"},
    "simpang_lima": {"lat": -6.9730, "lng": 110.4380, "name": "Simpang Lima"},
    "tembalang": {"lat": -6.9900, "lng": 110.4500, "name": "Tembalang"},
    "tugu": {"lat": -6.9550, "lng": 110.4150, "name": "Tugu"},
    "genuk_indah": {"lat": -6.9450, "lng": 110.4550, "name": "Genuk Indah"},
    "kleweran": {"lat": -6.9650, "lng": 110.4300, "name": "Kleweran"},
    "sunter": {"lat": -6.9350, "lng": 110.4300, "name": "Sunter"},
}


def fetch_historical_rainfall(
    lat: float,
    lng: float,
    start_date: str,
    end_date: str,
    rate_limiter: RateLimiter,
    cache: Cache,
) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum",
        "hourly": "precipitation,rain",
        "timezone": "Asia/Jakarta",
    }
    cache_key = f"openmeteo_hist_{lat}_{lng}_{start_date}_{end_date}"
    cached = cache.get_raw(cache_key)
    if cached:
        return cached

    rate_limiter.wait()
    try:
        resp = requests.get(OPEN_METEO_HISTORICAL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache.set_raw(cache_key, data)
        return data
    except Exception as e:
        print(f"  Error fetching historical for ({lat},{lng}): {e}")
        return None


def fetch_forecast_rainfall(
    lat: float,
    lng: float,
    rate_limiter: RateLimiter,
    cache: Cache,
) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "precipitation,rain,weathercode",
        "daily": "precipitation_sum,rain_sum",
        "timezone": "Asia/Jakarta",
        "forecast_days": 3,
    }
    cache_key = f"openmeteo_forecast_{lat}_{lng}"
    cached = cache.get_raw(cache_key)
    if cached:
        return cached

    rate_limiter.wait()
    try:
        resp = requests.get(OPEN_METEO_FORECAST, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache.set_raw(cache_key, data)
        return data
    except Exception as e:
        print(f"  Error fetching forecast for ({lat},{lng}): {e}")
        return None


def process_to_dataframe(data: dict, area_id: str, area_name: str) -> pd.DataFrame:
    records = []
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [])
    rain = hourly.get("rain", [])

    for i, t in enumerate(times):
        records.append({
            "area_id": area_id,
            "area_name": area_name,
            "datetime": t,
            "precipitation_mm": precip[i] if i < len(precip) else None,
            "rain_mm": rain[i] if i < len(rain) else None,
            "lat": data.get("latitude"),
            "lng": data.get("longitude"),
        })
    return pd.DataFrame(records)


def main():
    output_dir = Path(__file__).parent.parent / "data" / "raw" / "rainfall"
    output_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = Path(__file__).parent.parent / "data" / "raw" / "_cache"
    cache = Cache(str(cache_dir))
    rate_limiter = RateLimiter(min_interval=0.5)

    # Historical: last 2 years
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    log(f"Scraping rainfall data: {start_date} to {end_date}")
    log(f"Areas: {len(SEMARANG_AREAS)}")

    all_dfs = []

    for area_id, area in SEMARANG_AREAS.items():
        log(f"  Fetching historical: {area['name']} ({area_id})")
        data = fetch_historical_rainfall(
            area["lat"], area["lng"], start_date, end_date, rate_limiter, cache
        )
        if data:
            df = process_to_dataframe(data, area_id, area["name"])
            all_dfs.append(df)
            log(f"    Got {len(df)} hourly records")

        log(f"  Fetching forecast: {area['name']}")
        forecast = fetch_forecast_rainfall(
            area["lat"], area["lng"], rate_limiter, cache
        )
        if forecast:
            fc_path = output_dir / f"forecast_{area_id}.json"
            with open(fc_path, "w") as f:
                json.dump(forecast, f, indent=2)

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        out_path = output_dir / "semarang_rainfall_historical.csv"
        combined.to_csv(out_path, index=False)
        log(f"Saved {len(combined)} records to {out_path}")

        # Summary stats per area
        summary = combined.groupby("area_id").agg(
            area_name=("area_name", "first"),
            total_records=("precipitation_mm", "count"),
            total_precipitation=("precipitation_mm", "sum"),
            avg_hourly_precipitation=("precipitation_mm", "mean"),
            max_hourly_precipitation=("precipitation_mm", "max"),
            rainy_hours=("precipitation_mm", lambda x: (x > 0.5).sum()),
        ).reset_index()

        summary_path = output_dir / "semarang_rainfall_summary.csv"
        summary.to_csv(summary_path, index=False)
        log(f"Saved summary to {summary_path}")
        print("\n--- Summary ---")
        print(summary.to_string(index=False))
    else:
        log("No data collected!")

    log("Done.")


if __name__ == "__main__":
    main()
