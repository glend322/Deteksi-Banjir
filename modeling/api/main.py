import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    CVResult,
    PredictRequest,
    FloodPrediction,
    ReportInput,
    VerificationResult,
    FloodZoneResponse,
    FloodZone,
)
from dependencies import get_models, get_data, get_feature_cols

app = FastAPI(title="SafeRoute Modeling API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RISK_MAP = {0: "normal", 1: "waspada", 2: "tergenang"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/classify-image", response_model=CVResult)
async def classify_image(file: UploadFile = File(...)):
    return CVResult(
        flood_detected=False,
        severity="normal",
        depth_range="<20cm",
        depth_estimate_cm=0.0,
        confidence=0.5,
        bounding_boxes=[],
    )


@app.post("/api/predict-flood", response_model=FloodPrediction)
async def predict_flood(req: PredictRequest):
    clf, reg, scaler = get_models()
    df = get_data()
    feature_cols = get_feature_cols()

    if req.area_id:
        area_df = df[df["area_id"] == req.area_id].sort_values("date").tail(1)
    elif req.lat and req.lng:
        df["dist"] = np.sqrt((df["lat"] - req.lat) ** 2 + (df["lng"] - req.lng) ** 2)
        area_df = df.nsmallest(1, "dist")
    else:
        area_df = df.sort_values("date").groupby("area_id").tail(1)

    row = area_df.iloc[0]
    X = row[feature_cols].values.reshape(1, -1)
    X_scaled = scaler.transform(X)

    proba = clf.predict_proba(X_scaled)[0]
    flood_prob = float(sum(proba[1:]))
    depth_cm = float(reg.predict(X_scaled)[0])
    depth_cm = max(0, min(depth_cm, 200))

    if flood_prob > 0.8:
        risk = "tidak_dapat_dilalui"
    elif flood_prob > 0.5:
        risk = "tergenang"
    elif flood_prob > 0.2:
        risk = "waspada"
    else:
        risk = "normal"

    depth_buckets = [(0, 20, "<20cm"), (20, 40, "20-40cm"), (40, 70, "40-70cm"), (70, 200, ">70cm")]
    depth_range = ">70cm"
    for low, high, label in depth_buckets:
        if low <= depth_cm < high:
            depth_range = label
            break

    return FloodPrediction(
        area_id=row["area_id"],
        lat=float(row["lat"]),
        lng=float(row["lng"]),
        flood_probability=round(flood_prob, 4),
        predicted_depth_range=depth_range,
        time_window=req.time_window,
        confidence=round(float(max(proba)), 4),
        risk_level=risk,
    )


@app.post("/api/verify-report", response_model=VerificationResult)
async def verify_report(report: ReportInput):
    flags = []
    confidence = 0.5

    if report.lat and report.lng:
        _, _, scaler = get_models()
        df = get_data()
        feature_cols = get_feature_cols()

        df["dist"] = np.sqrt((df["lat"] - report.lat) ** 2 + (df["lng"] - report.lng) ** 2)
        nearby = df[df["dist"] < 0.02]
        if len(nearby) > 0:
            avg_precip = nearby["total_precipitation"].mean()
            if avg_precip > 10:
                confidence += 0.25
            elif avg_precip < 0.5:
                confidence -= 0.1
                flags.append("no_rain_nearby")

    if confidence > 0.7:
        status = "verified"
    elif confidence > 0.4:
        status = "unverified"
    else:
        status = "flagged"

    return VerificationResult(
        report_id=report.report_id,
        verification_status=status,
        confidence_score=round(min(confidence, 1.0), 4),
        flags=flags,
        estimated_depth=None,
    )


@app.get("/api/flood-zones", response_model=FloodZoneResponse)
async def get_flood_zones():
    clf, reg, scaler = get_models()
    df = get_data()
    feature_cols = get_feature_cols()

    zones = []
    for area_id in df["area_id"].unique():
        area_df = df[df["area_id"] == area_id].sort_values("date").tail(1)
        row = area_df.iloc[0]
        X = row[feature_cols].values.reshape(1, -1)
        X_scaled = scaler.transform(X)

        proba = clf.predict_proba(X_scaled)[0]
        flood_prob = float(sum(proba[1:]))
        depth_cm = float(reg.predict(X_scaled)[0])
        depth_cm = max(0, min(depth_cm, 200))

        if flood_prob > 0.8:
            risk = "tidak_dapat_dilalui"
        elif flood_prob > 0.5:
            risk = "tergenang"
        elif flood_prob > 0.2:
            risk = "waspada"
        else:
            risk = "normal"

        zones.append(FloodZone(
            id=area_id,
            name=row.get("area_name", area_id),
            lat=float(row["lat"]),
            lng=float(row["lng"]),
            depth=round(depth_cm, 1),
            status=risk,
            confidence=round(float(max(proba)), 4),
            last_updated=str(row["date"]),
            source="predictive_model",
        ))

    return FloodZoneResponse(zones=zones)


@app.get("/api/predictions")
async def get_predictions():
    clf, reg, scaler = get_models()
    df = get_data()
    feature_cols = get_feature_cols()

    predictions = []
    for area_id in df["area_id"].unique():
        area_df = df[df["area_id"] == area_id].sort_values("date").tail(1)
        row = area_df.iloc[0]
        X = row[feature_cols].values.reshape(1, -1)
        X_scaled = scaler.transform(X)

        proba = clf.predict_proba(X_scaled)[0]
        flood_prob = float(sum(proba[1:]))

        if flood_prob > 0.2:
            depth_cm = float(reg.predict(X_scaled)[0])
            predictions.append({
                "area_id": area_id,
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "flood_probability": round(flood_prob, 4),
                "depth_cm": round(max(0, min(depth_cm, 200)), 1),
                "date": str(row["date"]),
            })

    return {"predictions": predictions}
