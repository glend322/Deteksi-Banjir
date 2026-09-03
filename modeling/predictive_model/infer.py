"""
Inference script for the predictive flood model.

Usage:
  python infer.py --area kaligawe
  python infer.py --lat -6.942 --lng 110.42
  python infer.py --area kaligawe --time-window 6h
"""
import argparse
import json
import sys
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from dataset import load_data, add_temporal_features, FEATURE_COLS

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"

RISK_MAP = {0: "normal", 1: "waspada", 2: "tergenang"}
RISK_THRESHOLDS = {"normal": 0.2, "waspada": 0.5, "tergenang": 0.8}

DEPTH_BUCKETS = [
    (0, 20, "<20cm"),
    (20, 40, "20-40cm"),
    (40, 70, "40-70cm"),
    (70, 200, ">70cm"),
]


def load_model():
    with open(CHECKPOINT_DIR / "classifier.pkl", "rb") as f:
        clf = pickle.load(f)
    with open(CHECKPOINT_DIR / "regressor.pkl", "rb") as f:
        reg = pickle.load(f)
    with open(CHECKPOINT_DIR / "scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    return clf, reg, scaler


def get_depth_range(depth_cm: float) -> str:
    for low, high, label in DEPTH_BUCKETS:
        if low <= depth_cm < high:
            return label
    return ">70cm"


def predict_area(area_id: str = None, lat: float = None, lng: float = None, time_window: str = "3h"):
    clf, reg, scaler = load_model()
    df = load_data()
    df = add_temporal_features(df)

    all_feature_cols = FEATURE_COLS + [
        "day_of_week", "month", "day_of_year", "is_rainy_season"
    ]

    # Get latest data for the area
    if area_id:
        area_df = df[df["area_id"] == area_id].sort_values("date").tail(1)
    elif lat and lng:
        df["dist"] = np.sqrt((df["lat"] - lat) ** 2 + (df["lng"] - lng) ** 2)
        area_df = df.nsmallest(1, "dist").tail(1)
    else:
        area_df = df.sort_values("date").groupby("area_id").tail(1)

    results = []
    for _, row in area_df.iterrows():
        X = row[all_feature_cols].values.reshape(1, -1)
        X_scaled = scaler.transform(X)

        # Classification
        proba = clf.predict_proba(X_scaled)[0]
        pred_class = int(clf.predict(X_scaled)[0])
        risk_level = RISK_MAP.get(pred_class, "normal")

        # Regression
        depth_cm = float(reg.predict(X_scaled)[0])
        depth_cm = max(0, min(depth_cm, 200))
        depth_range = get_depth_range(depth_cm)

        # Confidence
        confidence = float(proba[pred_class])

        # Risk level based on probability thresholds
        flood_prob = float(sum(proba[1:]))
        if flood_prob > RISK_THRESHOLDS["tergenang"]:
            risk_level = "tidak_dapat_dilalui"
        elif flood_prob > RISK_THRESHOLDS["waspada"]:
            risk_level = "tergenang"
        elif flood_prob > RISK_THRESHOLDS["normal"]:
            risk_level = "waspada"

        result = {
            "area_id": row["area_id"],
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "date": str(row["date"]),
            "flood_probability": round(flood_prob, 4),
            "risk_level": risk_level,
            "confidence": round(confidence, 4),
            "depth_cm": round(depth_cm, 1),
            "depth_range": depth_range,
            "time_window": time_window,
            "probabilities": {
                "normal": round(float(proba[0]), 4),
                "waspada": round(float(proba[1]) if len(proba) > 1 else 0, 4),
                "tergenang": round(float(proba[2]) if len(proba) > 2 else 0, 4),
            },
        }
        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Flood prediction inference")
    parser.add_argument("--area", type=str, help="Area ID (e.g., kaligawe)")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lng", type=float, help="Longitude")
    parser.add_argument("--time-window", type=str, default="3h", help="Prediction window")
    parser.add_argument("--all", action="store_true", help="Predict for all areas")
    args = parser.parse_args()

    if args.all:
        df = load_data()
        areas = df["area_id"].unique()
        results = []
        for area in areas:
            results.extend(predict_area(area_id=area, time_window=args.time_window))
    elif args.area:
        results = predict_area(area_id=args.area, time_window=args.time_window)
    elif args.lat and args.lng:
        results = predict_area(lat=args.lat, lng=args.lng, time_window=args.time_window)
    else:
        results = predict_area(time_window=args.time_window)

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
