import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.decay_service import apply_confidence_decay
from app.services.weather_service import fetch_and_update_weather
from app.services.predictive_service import run_predictive_flood_engine

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None

# ─── Cooldown tracker untuk CCTV scan (deduplication) ────────────────────────
# Dict: slug → datetime terakhir deteksi dikirim ke backend
# Mencegah banjir request duplikat untuk kamera yang sama
_cctv_last_push: Dict[str, datetime] = {}
CCTV_COOLDOWN_MINUTES = 15  # Kamera sama tidak di-push lebih dari 1x/15menit


# ─────────────────────────────────────────────────────────────────────────────
# Job 1: Confidence Decay
# ─────────────────────────────────────────────────────────────────────────────
async def _job_confidence_decay():
    db = SessionLocal()
    try:
        result = apply_confidence_decay(db)
        logger.debug(f"[Scheduler] Decay selesai: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] Decay error: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Job 2: Weather Sync + Predictive Flood Engine
# ─────────────────────────────────────────────────────────────────────────────
async def _job_weather_and_predictive():
    db = SessionLocal()
    try:
        await fetch_and_update_weather(db)
        result = await run_predictive_flood_engine(db)
        alerts_active = result.get("alerts_active", 0)
        zones = result.get("total_zones_checked", 0)
        logger.info(f"[Scheduler] Predictive engine: {alerts_active} alert aktif dari {zones} zona DAS")
    except Exception as e:
        logger.error(f"[Scheduler] Weather/Predictive error: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Job 3: CCTV Scan — Integrasi Backend ↔ Modeling (P scheduler baru)
#
# Alur:
#   1. POST ke modeling API /api/scan-cctv
#   2. Filter deteksi yang flood_detected=True dan confidence >= threshold
#   3. Cek cooldown per kamera (CCTV_COOLDOWN_MINUTES)
#   4. Push hasil ke backend internal /api/internal/ai/predictions via API key
#
# Design decisions:
#   - Timeout scan: 30s (CCTV scan bisa lama)
#   - Cooldown per kamera: 15 menit (hindari duplikasi alert)
#   - Hanya push jika flood_detected=True DAN confidence >= 0.5
#   - Graceful: jika modeling offline, log warning dan skip (tidak crash)
# ─────────────────────────────────────────────────────────────────────────────
async def _job_cctv_scan():
    modeling_url = settings.MODELING_API_URL
    backend_url = f"http://localhost:8000{settings.API_V1_STR}"
    api_key = settings.INTERNAL_API_KEY
    confidence_threshold = 0.5

    logger.debug(f"[Scheduler] Memulai CCTV scan via {modeling_url}/api/scan-cctv ...")

    # 1. Panggil modeling service untuk scan semua kamera
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{modeling_url}/api/scan-cctv", json={})
            if resp.status_code != 200:
                logger.warning(f"[Scheduler] CCTV scan gagal: status {resp.status_code}")
                return
            scan_result = resp.json()
    except httpx.ConnectError:
        logger.debug("[Scheduler] Modeling API tidak tersedia, CCTV scan dilewati.")
        return
    except Exception as e:
        logger.warning(f"[Scheduler] CCTV scan error: {e}")
        return

    detections = scan_result.get("detections", [])
    total = scan_result.get("total_cameras", 0)
    pushed = 0
    skipped_cooldown = 0

    now = datetime.now(timezone.utc)

    for det in detections:
        # 2. Filter: hanya flood nyata dengan confidence cukup
        if not det.get("flood_detected", False):
            continue
        if det.get("confidence", 0.0) < confidence_threshold:
            continue

        cam_id = str(det.get("camera_id", ""))
        cam_name = det.get("camera_name", f"CCTV-{cam_id}")
        cooldown_key = f"cctv_{cam_id}"

        # 3. Cek cooldown — hindari push berulang untuk kamera sama
        last_push = _cctv_last_push.get(cooldown_key)
        if last_push:
            elapsed = (now - last_push).total_seconds() / 60
            if elapsed < CCTV_COOLDOWN_MINUTES:
                skipped_cooldown += 1
                continue

        # 4. Push ke backend internal /predictions
        payload = {
            "source_id": f"cctv_{cam_id}",
            "camera_name": cam_name,
            "lat": det.get("lat", -6.9535),
            "lng": det.get("lng", 110.4570),
            "flood_detected": True,
            "confidence": det.get("confidence", 0.5),
            "depth_estimate_cm": det.get("depth_estimate_cm", 30),  # dari CCTVFrameResult via depth_label
            "classification": det.get("classification", "sedang"),
            "area_name": det.get("area_name", "Semarang"),
            "status": det.get("status", "flooded"),
            "status_label": det.get("status_label", "Tergenang"),
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                push_resp = await client.post(
                    f"{backend_url}/internal/ai/predictions",
                    json=payload,
                    headers={"X-Internal-API-Key": api_key}
                )
                if push_resp.status_code in (200, 201):
                    _cctv_last_push[cooldown_key] = now
                    pushed += 1
                    logger.info(
                        f"[Scheduler] 🎥 CCTV '{cam_name}' → flood pushed "
                        f"(conf={det['confidence']:.2f}, depth≈{payload['depth_estimate_cm']}cm)"
                    )
                else:
                    logger.warning(f"[Scheduler] Push gagal untuk {cam_name}: {push_resp.status_code}")
        except Exception as e:
            logger.warning(f"[Scheduler] Push error untuk {cam_name}: {e}")

    logger.info(
        f"[Scheduler] CCTV scan selesai — {total} kamera | "
        f"{pushed} deteksi dipush | {skipped_cooldown} dilewati (cooldown)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle: Start & Stop
# ─────────────────────────────────────────────────────────────────────────────
def start_background_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler()

    # Job 1: Confidence Decay — setiap 30 menit
    _scheduler.add_job(
        _job_confidence_decay,
        trigger=IntervalTrigger(minutes=30),
        id="confidence_decay",
        name="Confidence Decay",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    # Job 2: Weather Sync + Predictive Engine — setiap 60 menit
    _scheduler.add_job(
        _job_weather_and_predictive,
        trigger=IntervalTrigger(minutes=60),
        id="weather_predictive",
        name="Weather Sync & Predictive Flood Engine",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120,
    )

    # Job 3: CCTV Scan — setiap 5 menit
    # Lebih sering dari decay/weather karena CCTV adalah real-time detection
    _scheduler.add_job(
        _job_cctv_scan,
        trigger=IntervalTrigger(minutes=5),
        id="cctv_scan",
        name="CCTV Scan & AI Push",
        replace_existing=True,
        max_instances=1,      # Tidak boleh overlap — satu scan selesai dulu baru scan berikutnya
        misfire_grace_time=30,
    )

    _scheduler.start()
    logger.info(
        "🚀 APScheduler dimulai — 3 job terdaftar: "
        "decay(30min) | weather+predictive(60min) | cctv-scan(5min)"
    )


def stop_background_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("🛑 APScheduler dimatikan.")
