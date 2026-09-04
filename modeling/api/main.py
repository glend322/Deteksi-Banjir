"""
FastAPI App — Modeling API Endpoints

Endpoints:
  POST /api/classify-image     — Classify a single image
  POST /api/scan-cctv          — Scan all CCTV cameras
  POST /api/calculate-route    — Calculate safe routes
  GET  /api/flood-zones        — Get active flood zones
  GET  /api/evacuation-points  — Get evacuation points
  GET  /health                 — Health check
"""
import io
import json
import logging
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from torchvision import transforms

from schemas import (
    CVResult,
    CCTVScanRequest,
    CCTVScanResponse,
    CCTVFrameResult,
    RouteCalculateRequest,
    RouteCalculateResponse,
    RouteOption,
    RoadLabel,
    FloodZone,
    FloodZoneResponse,
    EvacuationResult,
)
from dependencies import get_cv_model

logger = logging.getLogger(__name__)

app = FastAPI(title="SafeRoute Modeling API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_cv_inference(frame_bytes: bytes) -> dict:
    model, device = get_cv_model()

    img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(tensor)

    probs = torch.softmax(out["logits"], dim=1).cpu().numpy()[0]
    depth_cm = float(out["depth_cm"].cpu().numpy()[0])
    depth_cm = max(0.0, min(depth_cm, 200.0))

    pred_class = int(probs.argmax())
    confidence = float(probs[pred_class])
    flood_prob = float(probs[1]) if len(probs) > 1 else float(probs[pred_class])
    flood_detected = pred_class == 1 or flood_prob > 0.5

    if depth_cm < 20:
        classification = "dangkal"
    elif depth_cm < 40:
        classification = "sedang"
    else:
        classification = "dalam"

    return {
        "flood_detected": flood_detected,
        "classification": classification,
        "flood_probability": round(flood_prob, 4),
        "confidence": round(confidence, 4),
        "depth_estimate_cm": round(depth_cm, 1),
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/classify-image", response_model=CVResult)
async def classify_image(file: UploadFile = File(...)):
    frame_bytes = await file.read()
    result = _run_cv_inference(frame_bytes)

    return CVResult(
        flood_detected=result["flood_detected"],
        classification=result["classification"],
        depth_estimate_cm=result["depth_estimate_cm"],
        confidence=result["confidence"],
    )


@app.post("/api/scan-cctv", response_model=CCTVScanResponse)
async def scan_cctv(req: CCTVScanRequest):
    from cctv_client import CCTVClient
    from verifier import FalsePositiveFilter
    from area_mapping import get_area_name
    from classifier import classify_flood
    import asyncio

    client = CCTVClient(
        categories=req.categories or ["rawan_genangan", "sungai", "pompa_air"],
    )
    fp_filter = FalsePositiveFilter()

    cameras = await client.get_cameras(force_refresh=True)

    if req.camera_ids:
        cameras = [c for c in cameras if c.cctv_id in req.camera_ids]

    timestamp = time.time()
    total = len(cameras)
    scanned = 0
    successful = 0
    failed = 0
    detections = []

    semaphore = asyncio.Semaphore(5)

    async def _scan_one(cam):
        nonlocal scanned, successful, failed

        async with semaphore:
            scanned += 1
            frame = await client.extract_frame(cam)
            if not frame:
                failed += 1
                return None
            successful += 1

            try:
                cv_result = _run_cv_inference(frame)
            except Exception as e:
                logger.error(f"CV inference failed for {cam.name}: {e}")
                return None

            nparr = np.frombuffer(frame, np.uint8)
            frame_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            fp_result = fp_filter.filter(
                frame=frame_img,
                cv_result=cv_result,
                camera_id=f"cctv_{cam.cctv_id}_{cam.link_id}",
            )

            area_name = get_area_name(cam.lat, cam.lng)
            is_flood = (
                fp_result.is_genuine_flood
                and cv_result["confidence"] >= 0.5
                and cv_result["depth_estimate_cm"] >= 10
            )

            if is_flood:
                cls_result = classify_flood(cv_result["depth_estimate_cm"], area_name)
                classification = cls_result.classification
                status = cls_result.status
                status_label = cls_result.status_label
                color = cls_result.color
                notification = cls_result.notification
            else:
                classification = "normal"
                status = "safe"
                status_label = "Aman"
                color = "#10B981"
                notification = ""

            return CCTVFrameResult(
                camera_id=cam.cctv_id,
                camera_name=cam.name,
                lat=cam.lat,
                lng=cam.lng,
                stream_url=cam.stream_url,
                flood_detected=is_flood,
                classification=classification,
                depth_estimate_cm=cv_result["depth_estimate_cm"],
                confidence=max(0, min(1, cv_result["confidence"] + fp_result.confidence_modifier)),
                area_name=area_name,
                notification=notification,
                status=status,
                status_label=status_label,
                color=color,
                false_positive_filtered=not fp_result.is_genuine_flood and cv_result["flood_detected"],
                filter_reasons=fp_result.reasons,
                frame_timestamp=time.time(),
            )

    tasks = [_scan_one(cam) for cam in cameras]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, CCTVFrameResult):
            detections.append(r)

    return CCTVScanResponse(
        timestamp=timestamp,
        total_cameras=total,
        scanned_cameras=scanned,
        successful_frames=successful,
        failed_frames=failed,
        detections=detections,
    )


@app.post("/api/calculate-route", response_model=RouteCalculateResponse)
async def calculate_route(req: RouteCalculateRequest):
    from route_engine import calculate_safe_routes
    from evacuation_finder import find_nearest_evacuation

    flood_zones = []

    result = calculate_safe_routes(
        origin_lat=req.origin.lat,
        origin_lng=req.origin.lng,
        dest_lat=req.destination.lat,
        dest_lng=req.destination.lng,
        flood_zones=flood_zones,
        vehicle_max_depth_cm=req.vehicle_max_depth_cm or 30.0,
    )

    evacuation = find_nearest_evacuation(req.origin.lat, req.origin.lng)

    options = []
    for opt in result["options"]:
        road_labels = [
            RoadLabel(
                segment=rl["segment"],
                status=rl["status"],
                color=rl["color"],
                depth_cm=rl.get("depth_cm", 0),
            )
            for rl in opt.get("road_labels", [])
        ]
        options.append(RouteOption(
            id=opt["id"],
            type=opt["type"],
            title=opt["title"],
            badge=opt["badge"],
            duration=opt["duration"],
            distance=opt["distance"],
            flood_avoided=opt["flood_avoided"],
            risk_level=opt["risk_level"],
            color=opt["color"],
            description=opt["description"],
            path=opt["path"],
            road_labels=road_labels,
        ))

    evac_result = None
    if evacuation:
        evac_result = EvacuationResult(**evacuation)

    return RouteCalculateResponse(
        origin=req.origin.name or "Lokasi Saat Ini",
        destination=req.destination.name or "Tujuan",
        flood_zones_active=result["flood_zones_active"],
        options=options,
        nearest_evacuation=evac_result,
    )


@app.get("/api/flood-zones", response_model=FloodZoneResponse)
async def get_flood_zones():
    from area_mapping import get_area_name

    zones = []

    return FloodZoneResponse(zones=zones)


@app.get("/api/evacuation-points")
async def get_evacuation_points():
    from evacuation_finder import get_all_evacuation_points
    return get_all_evacuation_points()
