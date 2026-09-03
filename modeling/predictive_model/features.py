"""
Feature Engineering Pipeline

Combines scraped data (rainfall, OSM, DEM) into ML-ready features
for the predictive flood model.

Input:  data/raw/ (rainfall, osm, dem)
Output: data/processed/ (daily_features.csv, flood_targets.csv, geo_features.csv)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Real-world coordinates for each Semarang area
# Source: Known geographic locations of each kecamatan in Kota Semarang
AREA_COORDS = {
    "kaligawe":      {"lat": -6.9350, "lng": 110.4300, "area_name": "Kaligawe"},
    "genuk":         {"lat": -6.9420, "lng": 110.4550, "area_name": "Genuk"},
    "genuk_indah":   {"lat": -6.9450, "lng": 110.4600, "area_name": "Genuk Indah"},
    "semarang_utara":{"lat": -6.9600, "lng": 110.4200, "area_name": "Semarang Utara"},
    "tambakrejo":    {"lat": -6.9550, "lng": 110.4150, "area_name": "Tambakrejo"},
    "mangkang":      {"lat": -6.9700, "lng": 110.3950, "area_name": "Mangkang"},
    "gayamsari":     {"lat": -6.9750, "lng": 110.4450, "area_name": "Gayamsari"},
    "simpang_lima":  {"lat": -6.9730, "lng": 110.4380, "area_name": "Simpang Lima"},
    "tembalang":     {"lat": -6.9900, "lng": 110.4500, "area_name": "Tembalang"},
    "tugu":          {"lat": -7.0500, "lng": 110.3500, "area_name": "Tugu"},
    "kleweran":      {"lat": -6.9650, "lng": 110.4300, "area_name": "Kleweran"},
    "sunter":        {"lat": -6.9550, "lng": 110.4450, "area_name": "Sunter"},
}


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


def assign_area_coords_and_elevation(elev_df: pd.DataFrame) -> pd.DataFrame:
    """Assign real-world coordinates and nearest elevation to each area."""
    area_records = []
    for area_id, coords in AREA_COORDS.items():
        dists = np.sqrt(
            (elev_df["lat"] - coords["lat"]) ** 2 + (elev_df["lng"] - coords["lng"]) ** 2
        )
        nearest_idx = dists.idxmin()
        area_records.append({
            "area_id": area_id,
            "area_name": coords["area_name"],
            "lat": coords["lat"],
            "lng": coords["lng"],
            "elevation_m": elev_df.loc[nearest_idx, "elevation_m"],
        })
    return pd.DataFrame(area_records)


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


def compute_osm_features_for_areas(area_elev_df: pd.DataFrame, osm: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute geospatial features per area (nearest grid point lookup)."""
    features = area_elev_df.copy()

    # Drainage density: count waterways near each area
    if "waterways" in osm:
        ww = osm["waterways"].dropna(subset=["lat", "lng"])
        for idx, row in features.iterrows():
            dists = np.sqrt((ww["lat"] - row["lat"]) ** 2 + (ww["lng"] - row["lng"]) ** 2)
            nearby = (dists < 0.01).sum()  # ~1km radius
            features.loc[idx, "drainage_density"] = nearby

    # Water body proximity
    if "water_bodies" in osm:
        wb = osm["water_bodies"].dropna(subset=["lat", "lng"])
        for idx, row in features.iterrows():
            dists = np.sqrt((wb["lat"] - row["lat"]) ** 2 + (wb["lng"] - row["lng"]) ** 2)
            min_dist = float(dists.min()) if len(dists) > 0 else 999.0
            features.loc[idx, "nearest_water_body_dist"] = min_dist

    # Flood feature count
    if "flood_features" in osm:
        ff = osm["flood_features"].dropna(subset=["lat", "lng"])
        for idx, row in features.iterrows():
            dists = np.sqrt((ff["lat"] - row["lat"]) ** 2 + (ff["lng"] - row["lng"]) ** 2)
            nearby = (dists < 0.01).sum()
            features.loc[idx, "flood_feature_count"] = nearby

    # Land use distribution
    if "land_use" in osm:
        lu = osm["land_use"].dropna(subset=["lat", "lng"])
        for idx, row in features.iterrows():
            dists = np.sqrt((lu["lat"] - row["lat"]) ** 2 + (lu["lng"] - row["lng"]) ** 2)
            nearby = lu[dists < 0.02]
            for ltype in ["residential", "commercial", "industrial", "farmland", "forest"]:
                count = int((nearby["landuse"] == ltype).sum())
                features.loc[idx, f"landuse_{ltype}_count"] = count

    # Fill NaN geo features with 0
    for col in ["drainage_density", "nearest_water_body_dist", "flood_feature_count",
                "landuse_residential_count", "landuse_commercial_count",
                "landuse_industrial_count", "landuse_farmland_count", "landuse_forest_count"]:
        if col not in features.columns:
            features[col] = 0
        else:
            features[col] = features[col].fillna(0)

    return features


def create_sample_flood_targets(daily_features: pd.DataFrame) -> pd.DataFrame:
    """
    Create synthetic flood target labels based on rainfall + elevation + geo features.
    In production, these would come from actual flood incident records.

    Uses composite risk score:
    - Rainfall intensity (primary driver)
    - Elevation (lower = more flood-prone)
    - Drainage density (less drainage = more flood-prone)
    - Water body proximity (closer = more flood-prone)
    """
    targets = daily_features[["area_id", "area_name", "lat", "lng", "date"]].copy()

    precip = daily_features["total_precipitation"].fillna(0)

    # Normalize elevation to 0-1 risk factor (lower elev = higher risk)
    elev = daily_features["elevation_m"].fillna(50)
    elev_risk = 1.0 - np.clip(elev / 200.0, 0, 1)

    # Drainage density risk (less drainage = higher risk)
    drainage = daily_features.get("drainage_density", pd.Series(0, index=daily_features.index)).fillna(0)
    drainage_risk = 1.0 - np.clip(drainage / 10.0, 0, 1)

    # Water body proximity risk (closer = higher risk)
    water_dist = daily_features.get("nearest_water_body_dist", pd.Series(0.5, index=daily_features.index)).fillna(0.5)
    water_risk = 1.0 - np.clip(water_dist / 0.05, 0, 1)

    # Composite risk score: rainfall dominant, geo features as modifiers
    risk_score = (
        precip * 0.6 +
        precip * elev_risk * 0.2 +
        precip * drainage_risk * 0.1 +
        precip * water_risk * 0.1
    )

    conditions = [
        risk_score < 15,
        (risk_score >= 15) & (risk_score < 40),
        (risk_score >= 40) & (risk_score < 70),
        risk_score >= 70,
    ]
    choices = ["normal", "waspada", "tergenang", "tidak_dapat_dilalui"]
    targets["flood_risk"] = np.select(conditions, choices, default="normal")
    targets["flood_label"] = np.select(conditions, [0, 1, 2, 3], default=0)

    targets["estimated_depth_cm"] = np.clip(risk_score * 1.0, 0, 150)

    return targets


def main():
    print("Loading raw data...")
    rainfall = load_rainfall()
    elevation = load_elevation()
    osm = load_osm_features()

    print(f"  Rainfall: {len(rainfall)} records")
    print(f"  Elevation: {len(elevation)} points")
    print(f"  OSM features: {list(osm.keys())}")

    print("\nAssigning real-world coordinates and elevation to areas...")
    area_elev = assign_area_coords_and_elevation(elevation)
    print(f"  Area elevations:\n{area_elev.to_string()}")

    print("\nComputing geospatial features per area...")
    area_geo = compute_osm_features_for_areas(area_elev, osm)
    print(f"  Area geo features: {len(area_geo)} rows, cols: {list(area_geo.columns)}")

    # Update rainfall data with real area coordinates
    rainfall = rainfall.drop(columns=["lat", "lng"], errors="ignore")
    rainfall = rainfall.merge(
        area_elev[["area_id", "lat", "lng"]], on="area_id", how="left"
    )

    print("\nComputing daily rainfall features...")
    daily = compute_rainfall_features(rainfall)
    print(f"  Daily features: {len(daily)} rows")

    # Merge elevation into daily features
    daily = daily.merge(
        area_elev[["area_id", "elevation_m"]], on="area_id", how="left"
    )

    # Merge geo features into daily features
    geo_cols = ["area_id", "drainage_density", "nearest_water_body_dist",
                "flood_feature_count", "landuse_residential_count",
                "landuse_commercial_count", "landuse_industrial_count",
                "landuse_farmland_count", "landuse_forest_count"]
    daily = daily.merge(area_geo[geo_cols], on="area_id", how="left")

    # Fill any remaining NaN geo features
    for col in geo_cols[1:]:
        if col in daily.columns:
            daily[col] = daily[col].fillna(0)

    print("\nCreating flood target labels...")
    targets = create_sample_flood_targets(daily)
    print(f"  Target distribution:")
    print(targets["flood_risk"].value_counts().to_string())

    # Save processed data
    daily_path = PROCESSED_DIR / "daily_features.csv"
    daily.to_csv(daily_path, index=False)
    print(f"\nSaved daily features: {daily_path}")

    targets_path = PROCESSED_DIR / "flood_targets.csv"
    targets.to_csv(targets_path, index=False)
    print(f"Saved flood targets: {targets_path}")

    geo_path = PROCESSED_DIR / "geo_features.csv"
    area_geo.to_csv(geo_path, index=False)
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
        "geo_features_rows": len(area_geo),
        "areas": list(daily["area_id"].unique()),
    }
    with open(PROCESSED_DIR / "processing_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\nProcessing complete!")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
