from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    CVResult,
    PredictRequest,
    FloodPrediction,
    ReportInput,
    VerificationResult,
    FloodZoneResponse,
)

app = FastAPI(title="SafeRoute Modeling API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/classify-image", response_model=CVResult)
async def classify_image(file: UploadFile = File(...)):
    # TODO: Load CV model, run inference on uploaded image
    # Placeholder response
    return CVResult(
        flood_detected=True,
        severity="tergenang",
        depth_range="40-70cm",
        depth_estimate_cm=55.0,
        confidence=0.87,
        bounding_boxes=[],
    )


@app.post("/api/predict-flood", response_model=FloodPrediction)
async def predict_flood(req: PredictRequest):
    # TODO: Load predictive model, run inference
    # Placeholder response
    return FloodPrediction(
        area_id=req.area_id or "unknown",
        lat=req.lat or -6.968,
        lng=req.lng or 110.435,
        flood_probability=0.82,
        predicted_depth_range="20-40cm",
        time_window=req.time_window,
        confidence=0.78,
        risk_level="tergenang",
    )


@app.post("/api/verify-report", response_model=VerificationResult)
async def verify_report(report: ReportInput):
    # TODO: Load verifier, apply rules + ML scoring
    # Placeholder response
    return VerificationResult(
        report_id=report.report_id,
        verification_status="verified",
        confidence_score=0.91,
        flags=[],
        estimated_depth="20-40cm",
    )


@app.get("/api/flood-zones", response_model=FloodZoneResponse)
async def get_flood_zones():
    # TODO: Query model predictions + latest reports
    # Placeholder response
    return FloodZoneResponse(zones=[])


@app.get("/api/predictions")
async def get_predictions():
    # TODO: Return all active predictive alerts
    # Placeholder response
    return {"predictions": []}
