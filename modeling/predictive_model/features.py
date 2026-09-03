"""
Feature Engineering Pipeline

Combines scraped data (rainfall, OSM, DEM) into ML-ready features
for the predictive flood model.

Input:  data/raw/ (rainfall, osm, dem)
Output: data/processed/ (features.csv, targets.csv)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_rainfall() -> pd.DataFrame:
    path = RAW_DIR / "rainfall" / "semarang_rainfall_historical.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_elevation() -> pd.DataFrame:
    path = RAW_DIR / "dem" / "semarang_elevation_grid.csv"
    return pd.read_csv(path)


def load_osm_features() -> dict[str, pd.DataFrame]:
    osm_dir = RAW_DIR / "osm"
    features = {}
    for name in ["waterways", "land_use", "water_bodies", "roads", "flood_features"]:
        path = osm_dir / f"{name}.csv"
        if path.exists():
            features[name] = pd.read_csv(path)
    return features


def assign_area_by_nearest(rainfall_df: pd.DataFrame, elev_df: pd.DataFrame) -> pd.DataFrame:
    """Assign elevation to each rainfall area by nearest grid point."""
    area_coords = rainfall_df.groupby("area_id").agg(
        lat=("lat", "first"), lng=("lng", "first")
    ).reset_index()

    for _, row in area_coords.iterrows():
        dists = np.sqrt(
            (elev_df["lat"] - row["lat"]) ** 2 + (elev_df["lng"] - row["lng"]) ** 2
        )
        nearest_idx = dists.idxmin()
        area_coords.loc[area_coords["area_id"] == row["area_id"], "elevation_m"] = (
            elev_df.loc[nearest_idx, "elevation_m"]
        )

    return area_coords


def compute_rainfall_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rainfall aggregates per area per day."""
    df["date"] = df["datetime"].dt.date

    daily = df.groupby(["area_id", "area_name", "lat", "lng", "date"]).agg(
        total_precipitation=("precipitation_mm", "sum"),
        max_hourly_precipitation=("precipitation_mm", "max"),
        rainy_hours=("precipitation_mm", lambda x: (x > 0.5).sum()),
        precipitation_std=("precipitation_mm", "std"),
    ).reset_index()

    # Rolling aggregates (need to sort first)
    daily = daily.sort_values(["area_id", "date"])

    for window in [1, 3, 7]:
        daily[f"precip_sum_{window}d"] = daily.groupby("area_id")[
            "total_precipitation"
        ].transform(lambda x: x.rolling(window, min_periods=1).sum())

    # Max precipitation in last 3 days
    daily["precip_max_3d"] = daily.groupby("area_id")[
        "max_hourly_precipitation"
    ].transform(lambda x: x.rolling(3, min_periods=1).max())

    daily["date"] = pd.to_datetime(daily["date"])
    return daily


def compute_osm_features(elev_df: pd.DataFrame, osm: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute geospatial features per grid cell."""
    features = elev_df.copy()

    # Drainage density: count waterways near each point
    if "waterways" in osm:
        ww = osm["waterways"].dropna(subset=["lat", "lng"])
        for _, row in features.iterrows():
            dists = np.sqrt((ww["lat"] - row["lat"]) ** 2 + (ww["lng"] - row["lng"]) ** 2)
            nearby = (dists < 0.01).sum()  # ~1km radius
            features.loc[features.index[features["lat"] == row["lat"]], "drainage_density"] = nearby

    # Water body proximity
    if "water_bodies" in osm:
        wb = osm["water_bodies"].dropna(subset=["lat", "lng"])
        for _, row in features.iterrows():
            dists = np.sqrt((wb["lat"] - row["lat"]) ** 2 + (wb["lng"] - row["lng"]) ** 2)
            min_dist = dists.min() if len(dists) > 0 else 999
            features.loc[features.index[features["lat"] == row["lat"]], "nearest_water_body_dist"] = min_dist

    # Flood feature count
    if "flood_features" in osm:
        ff = osm["flood_features"].dropna(subset=["lat", "lng"])
        for _, row in features.iterrows():
            dists = np.sqrt((ff["lat"] - row["lat"]) ** 2 + (ff["lng"] - row["lng"]) ** 2)
            nearby = (dists < 0.01).sum()
            features.loc[features.index[features["lat"] == row["lat"]], "flood_feature_count"] = nearby

    # Land use distribution
    if "land_use" in osm:
        lu = osm["land_use"].dropna(subset=["lat", "lng"])
        for _, row in features.iterrows():
            dists = np.sqrt((lu["lat"] - row["lat"]) ** 2 + (lu["lng"] - row["lng"]) ** 2)
            nearby = lu[dists < 0.02]
            for ltype in ["residential", "commercial", "industrial", "farmland", "forest"]:
                count = (nearby["landuse"] == ltype).sum()
                col = f"landuse_{ltype}_count"
                features.loc[features.index[features["lat"] == row["lat"]], col] = count

    return features


def create_sample_flood_targets(daily_features: pd.DataFrame) -> pd.DataFrame:
    """
    Create synthetic flood target labels based on rainfall thresholds.
    In production, these would come from actual flood incident records.

    Thresholds (inspired by Semarang flood patterns):
    - Normal: precip_sum_1d < 20mm
    - Waspada: 20mm <= precip_sum_1d < 50mm
    - Tergenang: 50mm <= precip_sum_1d < 80mm
    - Tidak Dapat Dilalui: precip_sum_1d >= 80mm
    """
    targets = daily_features[["area_id", "area_name", "lat", "lng", "date"]].copy()

    precip = daily_features["total_precipitation"].fillna(0)

    conditions = [
        precip < 20,
        (precip >= 20) & (precip < 50),
        (precip >= 50) & (precip < 80),
        precip >= 80,
    ]
    choices = ["normal", "waspada", "tergenang", "tidak_dapat_dilalui"]
    targets["flood_risk"] = np.select(conditions, choices, default="normal")
    targets["flood_label"] = np.select(conditions, [0, 1, 2, 3], default=0)

    # Estimated depth based on rainfall
    targets["estimated_depth_cm"] = np.clip(precip * 0.8, 0, 150)

    return targets


def main():
    print("Loading raw data...")
    rainfall = load_rainfall()
    elevation = load_elevation()
    osm = load_osm_features()

    print(f"  Rainfall: {len(rainfall)} records")
    print(f"  Elevation: {len(elevation)} points")
    print(f"  OSM features: {list(osm.keys())}")

    print("\nAssigning elevation to areas...")
    area_elev = assign_area_by_nearest(rainfall, elevation)
    print(f"  Area elevations:\n{area_elev.to_string()}")

    print("\nComputing daily rainfall features...")
    daily = compute_rainfall_features(rainfall)
    print(f"  Daily features: {len(daily)} rows")

    print("\nComputing geospatial features...")
    geo_features = compute_osm_features(elevation, osm)
    print(f"  Geo features: {len(geo_features)} rows, cols: {list(geo_features.columns)}")

    print("\nCreating flood target labels...")
    targets = create_sample_flood_targets(daily)
    print(f"  Target distribution:")
    print(targets["flood_risk"].value_counts().to_string())

    # Merge elevation into daily features
    daily = daily.merge(
        area_elev[["area_id", "elevation_m"]], on="area_id", how="left"
    )

    # Save processed data
    daily_path = PROCESSED_DIR / "daily_features.csv"
    daily.to_csv(daily_path, index=False)
    print(f"\nSaved daily features: {daily_path}")

    targets_path = PROCESSED_DIR / "flood_targets.csv"
    targets.to_csv(targets_path, index=False)
    print(f"Saved flood targets: {targets_path}")

    geo_path = PROCESSED_DIR / "geo_features.csv"
    geo_features.to_csv(geo_path, index=False)
    print(f"Saved geo features: {geo_path}")

    area_elev_path = PROCESSED_DIR / "area_elevations.csv"
    area_elev.to_csv(area_elev_path, index=False)
    print(f"Saved area elevations: {area_elev_path}")

    # Summary
    summary = {
        "daily_features_rows": len(daily),
        "daily_features_cols": list(daily.columns),
        "targets_rows": len(targets),
        "target_distribution": targets["flood_risk"].value_counts().to_dict(),
        "geo_features_rows": len(geo_features),
        "areas": list(daily["area_id"].unique()),
    }
    with open(PROCESSED_DIR / "processing_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\nProcessing complete!")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
