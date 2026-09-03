"""
Dataset loader for the predictive flood model.

Merges daily rainfall features with flood targets,
handles train/val/test splits, and provides DataLoaders.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

# Core rainfall + elevation features
BASE_FEATURE_COLS = [
    "total_precipitation",
    "max_hourly_precipitation",
    "rainy_hours",
    "precipitation_std",
    "precip_sum_1d",
    "precip_sum_3d",
    "precip_sum_7d",
    "precip_max_3d",
    "elevation_m",
    "lat",
    "lng",
]

# Geospatial features from OSM
GEO_FEATURE_COLS = [
    "drainage_density",
    "nearest_water_body_dist",
    "flood_feature_count",
    "landuse_residential_count",
    "landuse_commercial_count",
    "landuse_industrial_count",
    "landuse_farmland_count",
    "landuse_forest_count",
]

# Temporal features
TEMPORAL_FEATURE_COLS = [
    "day_of_week",
    "month",
    "day_of_year",
    "is_rainy_season",
]


def load_data() -> pd.DataFrame:
    features = pd.read_csv(PROCESSED_DIR / "daily_features.csv")
    targets = pd.read_csv(PROCESSED_DIR / "flood_targets.csv")
    merged = features.merge(
        targets[["area_id", "date", "flood_risk", "flood_label", "estimated_depth_cm"]],
        on=["area_id", "date"],
        how="left",
    )
    return merged


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["is_rainy_season"] = df["month"].isin([10, 11, 12, 1, 2, 3, 4]).astype(int)
    return df


def get_feature_cols() -> list[str]:
    """Return all feature columns, filtering out any that don't exist in the data."""
    return BASE_FEATURE_COLS + GEO_FEATURE_COLS + TEMPORAL_FEATURE_COLS


def prepare_splits(
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = 42,
):
    df = load_data()
    df = add_temporal_features(df)

    all_feature_cols = get_feature_cols()
    # Filter to columns that actually exist in the data
    all_feature_cols = [c for c in all_feature_cols if c in df.columns]
    # Fill NaN in features
    df[all_feature_cols] = df[all_feature_cols].fillna(0)

    X = df[all_feature_cols].values
    y_class = df["flood_label"].values
    y_depth = df["estimated_depth_cm"].values

    # Temporal split: last 15% = test, previous 15% = val
    df_sorted = df.sort_values("date").reset_index(drop=True)
    n = len(df_sorted)
    test_start = int(n * (1 - test_size))
    val_start = int(n * (1 - test_size - val_size))

    train_idx = df_sorted.index[:val_start]
    val_idx = df_sorted.index[val_start:test_start]
    test_idx = df_sorted.index[test_start:]

    X_train, y_train_c, y_train_d = X[train_idx], y_class[train_idx], y_depth[train_idx]
    X_val, y_val_c, y_val_d = X[val_idx], y_class[val_idx], y_depth[val_idx]
    X_test, y_test_c, y_test_d = X[test_idx], y_class[test_idx], y_depth[test_idx]

    # Fit scaler on train only (no data leakage)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    return {
        "X_train": X_train, "y_train_class": y_train_c, "y_train_depth": y_train_d,
        "X_val": X_val, "y_val_class": y_val_c, "y_val_depth": y_val_d,
        "X_test": X_test, "y_test_class": y_test_c, "y_test_depth": y_test_d,
        "feature_names": all_feature_cols,
        "scaler": scaler,
        "df": df,
    }


if __name__ == "__main__":
    data = prepare_splits()
    print(f"Train: {data['X_train'].shape}")
    print(f"Val:   {data['X_val'].shape}")
    print(f"Test:  {data['X_test'].shape}")
    print(f"Features: {data['feature_names']}")
    print(f"Train class dist: {np.bincount(data['y_train_class'].astype(int))}")
    print(f"Val class dist:   {np.bincount(data['y_val_class'].astype(int))}")
    print(f"Test class dist:  {np.bincount(data['y_test_class'].astype(int))}")
