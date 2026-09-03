"""
DEM Elevation Data Downloader

Downloads SRTM DEM tiles for Semarang from USGS.
Uses the SRTM 30m resolution tiles.

Alternative: Open-Meteo elevation API for point elevations.
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import RateLimiter, Cache, log, download_file, SEMARANG_BOUNDS

# Open-Meteo elevation API (free, no key)
OPEN_METEO_ELEVATION = "https://api.open-meteo.com/v1/elevation"


def fetch_elevation_points(
    lats: list[float],
    lngs: list[float],
    rate_limiter: RateLimiter,
    cache: Cache,
) -> dict | None:
    """Fetch elevation for multiple points using Open-Meteo."""
    cache_key = f"elevation_{len(lats)}_points"
    cached = cache.get_raw(cache_key)
    if cached:
        return cached

    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat in lats),
        "longitude": ",".join(f"{lng:.4f}" for lng in lngs),
    }
    rate_limiter.wait()
    try:
        resp = requests.get(OPEN_METEO_ELEVATION, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache.set_raw(cache_key, data)
        return data
    except Exception as e:
        print(f"  Error fetching elevation: {e}")
        return None


def generate_grid_points(bounds: dict, step_km: float = 1.0) -> list[tuple[float, float]]:
    """Generate a grid of points within bounds."""
    import math

    lat_step = step_km / 111.0  # ~111 km per degree latitude
    lng_step = step_km / (111.0 * math.cos(math.radians((bounds["lat_min"] + bounds["lat_max"]) / 2)))

    points = []
    lat = bounds["lat_min"]
    while lat <= bounds["lat_max"]:
        lng = bounds["lng_min"]
        while lng <= bounds["lng_max"]:
            points.append((round(lat, 4), round(lng, 4)))
            lng += lng_step
        lat += lat_step
    return points


def main():
    output_dir = Path(__file__).parent.parent / "data" / "raw" / "dem"
    output_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = Path(__file__).parent.parent / "data" / "raw" / "_cache"
    cache = Cache(str(cache_dir))
    rate_limiter = RateLimiter(min_interval=0.5)

    log("Generating elevation grid for Semarang...")
    points = generate_grid_points(SEMARANG_BOUNDS, step_km=0.5)
    log(f"  {len(points)} points to query")

    # Open-Meteo can handle multiple points at once
    batch_size = 50
    all_results = []

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        lats = [p[0] for p in batch]
        lngs = [p[1] for p in batch]

        log(f"  Batch {i // batch_size + 1}: points {i+1}-{min(i+batch_size, len(points))}")
        data = fetch_elevation_points(lats, lngs, rate_limiter, cache)

        if data and "elevation" in data:
            for j, elev in enumerate(data["elevation"]):
                all_results.append({
                    "lat": lats[j],
                    "lng": lngs[j],
                    "elevation_m": elev,
                })

    if all_results:
        import pandas as pd
        df = pd.DataFrame(all_results)
        out_path = output_dir / "semarang_elevation_grid.csv"
        df.to_csv(out_path, index=False)
        log(f"Saved {len(df)} elevation points to {out_path}")

        stats = {
            "min_elevation_m": df["elevation_m"].min(),
            "max_elevation_m": df["elevation_m"].max(),
            "mean_elevation_m": round(df["elevation_m"].mean(), 2),
            "points_count": len(df),
        }
        with open(output_dir / "elevation_stats.json", "w") as f:
            json.dump(stats, f, indent=2)

        print(f"\n--- Elevation Stats ---")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    else:
        log("No elevation data collected!")

    log("Done.")


if __name__ == "__main__":
    main()
