"""
Flood Detection Pipeline — Orchestrator

Full pipeline: CCTV → CV → Verify → Classify → Output

Usage:
  python detector.py --once
  python detector.py --interval 60
"""
import asyncio
import io
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

ROOT_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("detector")


@dataclass
class FloodDetection:
    camera_id: int
    camera_name: str
    lat: float
    lng: float
    area_name: str
    is_flood: bool
    depth_cm: float
    classification: str
    confidence: float
    is_false_positive: bool
    notification: str
    timestamp: float
    status: str = ""
    status_label: str = ""
    color: str = ""

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "lat": self.lat,
            "lng": self.lng,
            "area_name": self.area_name,
            "is_flood": self.is_flood,
            "depth_cm": self.depth_cm,
            "classification": self.classification,
            "confidence": self.confidence,
            "is_false_positive": self.is_false_positive,
            "notification": self.notification,
            "status": self.status,
            "status_label": self.status_label,
            "color": self.color,
            "timestamp": self.timestamp,
        }


class FloodDetectionPipeline:
    """
    CCTV → CV Detection → Verification → Classification → Output
    """

    def __init__(self):
        self._cctv_client = None
        self._fp_filter = None
        self._cv_model = None
        self._cv_device = None
        self._initialized = False

    def _init(self):
        from cctv_client import CCTVClient
        from verifier import FalsePositiveFilter
        from cv_model import FloodClassifier

        logger.info("Initializing pipeline components...")

        self._cctv_client = CCTVClient(
            categories=["rawan_genangan", "sungai", "pompa_air"],
            cache_dir=ROOT_DIR / "cache" / "cctv",
        )

        self._fp_filter = FalsePositiveFilter(history_size=10)

        self._cv_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ckpt_path = ROOT_DIR / "checkpoints" / "best.pt"

        if ckpt_path.exists():
            ckpt = torch.load(ckpt_path, map_location=self._cv_device, weights_only=False)
            backbone = ckpt.get("backbone", "resnet50")
            self._cv_model = FloodClassifier(num_classes=2, pretrained=False, backbone=backbone)
            self._cv_model.load_state_dict(ckpt["model_state_dict"])
            logger.info(f"CV model loaded from {ckpt_path} (backbone={backbone})")
        else:
            logger.warning("No checkpoint found, using pretrained model")
            self._cv_model = FloodClassifier(num_classes=2, pretrained=True, backbone="mobilenet_v3_small")

        self._cv_model.to(self._cv_device)
        self._cv_model.eval()

        self._initialized = True
        logger.info("Pipeline initialized successfully")

    def _run_cv_inference(self, frame_bytes: bytes) -> dict:
        from cv_model import CLASS_NAMES, depth_to_classification

        img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        tensor = transform(img).unsqueeze(0).to(self._cv_device)

        with torch.no_grad():
            out = self._cv_model(tensor)

        probs = torch.softmax(out["logits"], dim=1).cpu().numpy()[0]
        depth_cm = float(out["depth_cm"].cpu().numpy()[0])
        depth_cm = max(0.0, min(depth_cm, 200.0))

        pred_class = int(probs.argmax())
        confidence = float(probs[pred_class])
        flood_prob = float(probs[1]) if len(probs) > 1 else float(probs[pred_class])

        flood_detected = pred_class == 1 or flood_prob > 0.5

        return {
            "flood_detected": flood_detected,
            "class_name": CLASS_NAMES[pred_class],
            "flood_probability": round(flood_prob, 4),
            "confidence": round(confidence, 4),
            "depth_estimate_cm": round(depth_cm, 1),
        }

    def _run_false_positive_filter(self, frame_bytes: bytes, cv_result: dict, camera_id: str):
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return False, ["failed_to_decode_frame"], 0.0

        fp_result = self._fp_filter.filter(
            frame=frame,
            cv_result=cv_result,
            camera_id=camera_id,
        )

        return fp_result.is_genuine_flood, fp_result.reasons, fp_result.confidence_modifier

    async def detect_single_camera(self, camera) -> Optional[FloodDetection]:
        try:
            frame_bytes = await self._cctv_client.extract_frame(camera)
            if not frame_bytes:
                return None

            cv_result = self._run_cv_inference(frame_bytes)

            cam_key = f"cctv_{camera.cctv_id}_{camera.link_id}"
            is_genuine, filter_reasons, conf_mod = self._run_false_positive_filter(
                frame_bytes, cv_result, cam_key
            )

            from area_mapping import get_area_name
            area_name = get_area_name(camera.lat, camera.lng)

            final_confidence = max(0.0, min(1.0, cv_result["confidence"] + conf_mod))
            is_false_positive = cv_result["flood_detected"] and not is_genuine

            is_flood = (
                is_genuine
                and final_confidence >= 0.5
                and cv_result["depth_estimate_cm"] >= 10
            )

            from classifier import classify_flood
            if is_flood:
                cls_result = classify_flood(cv_result["depth_estimate_cm"], area_name)
            else:
                cls_result = classify_flood(0, area_name)
                cls_result.classification = "normal"
                cls_result.status = "safe"
                cls_result.status_label = "Aman"
                cls_result.color = "#10B981"
                cls_result.notification = ""

            return FloodDetection(
                camera_id=camera.cctv_id,
                camera_name=camera.name,
                lat=camera.lat,
                lng=camera.lng,
                area_name=area_name,
                is_flood=is_flood,
                depth_cm=cv_result["depth_estimate_cm"],
                classification=cls_result.classification,
                confidence=final_confidence,
                is_false_positive=is_false_positive,
                notification=cls_result.notification,
                timestamp=time.time(),
                status=cls_result.status,
                status_label=cls_result.status_label,
                color=cls_result.color,
            )

        except Exception as e:
            logger.error(f"Error detecting {camera.name}: {e}")
            return None

    async def run_scan(self) -> list[FloodDetection]:
        if not self._initialized:
            self._init()

        cameras = await self._cctv_client.get_cameras(force_refresh=True)
        logger.info(f"Scanning {len(cameras)} cameras...")

        detections = []
        flood_detections = []

        semaphore = asyncio.Semaphore(5)

        async def _scan_one(cam):
            async with semaphore:
                return await self.detect_single_camera(cam)

        tasks = [_scan_one(cam) for cam in cameras]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, FloodDetection):
                detections.append(r)
                if r.is_flood:
                    flood_detections.append(r)

        logger.info(f"\n{'='*60}")
        logger.info(f"SCAN RESULTS: {len(detections)} cameras scanned")
        logger.info(f"{'='*60}")

        if flood_detections:
            logger.info(f"\nFLOOD DETECTED ({len(flood_detections)} locations):")
            for d in flood_detections:
                logger.info(f"  {d.notification}")
                logger.info(f"    Camera: {d.camera_name} | {d.classification} | {d.depth_cm}cm | conf: {d.confidence:.2f}")
        else:
            logger.info("\nNo flooding detected.")

        logger.info(f"{'='*60}\n")

        return detections

    async def _run_forever(self, interval: int = 60):
        logger.info(f"Starting continuous monitoring (interval={interval}s)...")
        while True:
            try:
                await self.run_scan()
            except Exception as e:
                logger.error(f"Scan error: {e}")
            await asyncio.sleep(interval)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Flood Detection Pipeline")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval (seconds)")
    parser.add_argument("--once", action="store_true", help="Run single scan then exit")
    args = parser.parse_args()

    pipeline = FloodDetectionPipeline()

    if args.once:
        detections = asyncio.run(pipeline.run_scan())
        results = [d.to_dict() for d in detections if d.is_flood]
        if results:
            print("\n=== FLOOD DETECTIONS ===")
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("\nNo flooding detected.")
    else:
        asyncio.run(pipeline._run_forever(args.interval))


if __name__ == "__main__":
    main()
