"""
Flood Detection Background Worker

Periodically scans CCTV cameras, runs CV flood detection pipeline,
and sends notifications when flooding is detected.

Usage:
  python worker.py
  python worker.py --interval 60 --confidence-threshold 0.5
"""
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT_DIR / "worker.log"),
    ],
)
logger = logging.getLogger("flood_worker")


@dataclass
class WorkerConfig:
    scan_interval: int = 60
    confidence_threshold: float = 0.5
    depth_threshold_cm: float = 10.0
    cooldown_minutes: int = 15
    backend_url: str = "http://localhost:8000"


@dataclass
class AlertState:
    camera_alerts: dict = field(default_factory=dict)

    def should_alert(self, camera_id: str, cooldown_minutes: int) -> bool:
        last = self.camera_alerts.get(camera_id, 0)
        return (time.time() - last) > cooldown_minutes * 60

    def record_alert(self, camera_id: str):
        self.camera_alerts[camera_id] = time.time()

    def cleanup(self, max_age_minutes: int = 60):
        cutoff = time.time() - max_age_minutes * 60
        self.camera_alerts = {k: v for k, v in self.camera_alerts.items() if v > cutoff}


class FloodDetectionWorker:
    """
    Background worker for CCTV flood detection.

    Pipeline per scan cycle:
    1. Scrape CCTV cameras from Pantau Semar
    2. Extract frames from HLS streams
    3. Run CV flood classification
    4. Apply false positive filters
    5. Classify: dangkal / sedang / dalam
    6. Output: "Daerah X banjir di tingkat Y"
    7. Send to backend + trigger notification
    """

    def __init__(self, config: WorkerConfig | None = None):
        self.config = config or WorkerConfig()
        self._alert_state = AlertState()
        self._pipeline = None
        self._running = False
        self._scan_count = 0

    def _init_pipeline(self):
        from flood_detection.detector import FloodDetectionPipeline
        self._pipeline = FloodDetectionPipeline()
        self._pipeline._init()

    async def _send_flood_alert(self, detection):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "source_name": "CCTV Pantau Semarang",
                    "location_name": detection.camera_name,
                    "area": detection.area_name,
                    "lat": detection.lat,
                    "lng": detection.lng,
                    "estimated_depth_cm": int(detection.depth_cm),
                    "classification": detection.classification,
                    "confidence": int(detection.confidence * 100),
                    "alert_needed": True,
                    "cause": "Deteksi CCTV AI Real-Time",
                }
                resp = await client.post(
                    f"{self.config.backend_url}/api/internal/ai/predictions",
                    json=payload,
                )
                if resp.status_code in (200, 201):
                    logger.info(f"Alert saved to backend for {detection.area_name}")
                else:
                    logger.warning(f"Backend returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to save alert to backend: {e}")

    async def scan_cycle(self):
        self._scan_count += 1
        logger.info(f"--- Scan cycle #{self._scan_count} started ---")

        self._alert_state.cleanup()
        detections = await self._pipeline.run_scan()

        alerts_this_cycle = 0
        for det in detections:
            if det.is_flood:
                cam_key = f"{det.camera_id}_{det.camera_name}"
                if self._alert_state.should_alert(cam_key, self.config.cooldown_minutes):
                    logger.info(f"ALERT: {det.notification}")
                    logger.info(f"  Camera: {det.camera_name} | {det.classification} | {det.depth_cm}cm | conf: {det.confidence:.2f}")
                    await self._send_flood_alert(det)
                    self._alert_state.record_alert(cam_key)
                    alerts_this_cycle += 1

        logger.info(f"--- Scan cycle #{self._scan_count} complete: {alerts_this_cycle} alerts sent ---")

    async def run(self):
        self._init_pipeline()
        self._running = True
        logger.info(f"Worker started | interval={self.config.scan_interval}s")

        while self._running:
            try:
                await self.scan_cycle()
            except Exception as e:
                logger.error(f"Scan cycle error: {e}", exc_info=True)
            await asyncio.sleep(self.config.scan_interval)

    def stop(self):
        self._running = False
        logger.info("Worker stopping...")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Flood Detection Worker")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval (seconds)")
    parser.add_argument("--confidence-threshold", type=float, default=0.5)
    parser.add_argument("--cooldown", type=int, default=15, help="Cooldown between alerts (minutes)")
    args = parser.parse_args()

    config = WorkerConfig(
        scan_interval=args.interval,
        confidence_threshold=args.confidence_threshold,
        cooldown_minutes=args.cooldown,
    )

    worker = FloodDetectionWorker(config)

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()
