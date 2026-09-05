import asyncio
import logging
from app.core.database import SessionLocal
from app.services.decay_service import apply_confidence_decay
from app.services.weather_service import fetch_and_update_weather
from app.services.predictive_service import run_predictive_flood_engine

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task = None
_running: bool = False

async def background_scheduler_loop():
    """
    Background Worker:
    1. Confidence Decay (Freshness Data) setiap 30 menit
    2. Live Weather Sync & Predictive Flood Early Warning setiap 60 menit
    """
    logger.info("⏰ Background Scheduler SafeRoute Semarang dimulai...")
    iter_count = 0
    
    while _running:
        try:
            db = SessionLocal()
            try:
                # 1. Jalankan Confidence Decay
                decay_result = apply_confidence_decay(db)
                logger.debug(f"[Scheduler] Confidence decay: {decay_result}")

                # 2. Sinkronisasi Cuaca & Prediksi Dini (Setiap jam atau iterasi awal)
                if iter_count % 2 == 0:
                    await fetch_and_update_weather(db)
                    pred_result = await run_predictive_flood_engine(db)
                    logger.debug(f"[Scheduler] Predictive engine: {pred_result.get('status')}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"[Scheduler Error] Terjadi kendala pada background worker: {e}")

        iter_count += 1
        # Sleep 1800 detik (30 menit)
        try:
            await asyncio.sleep(1800)
        except asyncio.CancelledError:
            logger.info("⏰ Background Scheduler dibatalkan (Server Shutdown).")
            break

def start_background_scheduler():
    global _scheduler_task, _running
    if not _running:
        _running = True
        _scheduler_task = asyncio.create_task(background_scheduler_loop())
        logger.info("🚀 Background Scheduler task terdaftar di event loop.")

def stop_background_scheduler():
    global _scheduler_task, _running
    if _running:
        _running = False
        if _scheduler_task and not _scheduler_task.done():
            _scheduler_task.cancel()
        logger.info("🛑 Background Scheduler dimatikan.")

