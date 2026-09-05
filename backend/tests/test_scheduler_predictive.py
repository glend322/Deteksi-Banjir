import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models.flood import FloodPoint
from app.models.weather import Alert
from app.services.decay_service import apply_confidence_decay
from app.services.predictive_service import (
    fetch_spot_weather,
    run_predictive_flood_engine
)

def test_scheduler_and_predictive():
    print("==================================================")
    print("⏰ RUNNING BACKGROUND SCHEDULER & PREDICTIVE TESTS")
    print("==================================================")

    # 1. Test Confidence Decay (Data Freshness & Auto-Receding)
    print("\n[TEST 1] Testing Confidence Decay & Auto-Receding Water...")
    now = datetime.now(timezone.utc)

    # Point 1: 3 jam yang lalu (Confidence 90 -> 90 - 15 = 75)
    point_recent = FloodPoint(
        id=1,
        slug="loc-recent",
        name="Jl. Muktiharjo",
        status="flooded",
        confidence=90,
        depth_cm=30,
        updated_at=now - timedelta(hours=3)
    )

    # Point 2: 8 jam yang lalu dengan confidence rendah (15 -> auto-receding to safe)
    point_old = FloodPoint(
        id=2,
        slug="loc-old",
        name="Jl. Genuk Sari",
        status="watch",
        confidence=20,
        depth_cm=15,
        updated_at=now - timedelta(hours=8)
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [point_recent, point_old]

    decay_result = apply_confidence_decay(mock_db)
    print("-> Decay result summary:", decay_result)

    assert point_recent.confidence == 75, f"Expected 75, got {point_recent.confidence}"
    assert point_old.status == "safe", f"Expected 'safe', got {point_old.status}"
    assert point_old.depth_cm == 0
    print("✅ Confidence decay & auto-receding test passed.")

    # 2. Test Spot Weather Helper
    print("\n[TEST 2] Testing fetch_spot_weather for Semarang Atas...")
    spot_res = asyncio.run(fetch_spot_weather(-7.0505, 110.4410))
    print("-> Spot weather:", spot_res)
    assert "condition" in spot_res
    assert "precipitation" in spot_res
    print("✅ Spot weather helper test passed.")

    # 3. Test Predictive Flood Early Warning Engine
    print("\n[TEST 3] Testing Predictive Flood Early Warning (Upstream Cloudburst Simulation)...")
    mock_kaligawe = FloodPoint(
        id=10,
        slug="loc-kaligawe",
        name="Jl. Kaligawe Raya",
        status="safe",
        depth_cm=0
    )

    mock_db_pred = MagicMock()
    # Mock query: first call for Alert, second call for FloodPoint
    def mock_query_pred_side_effect(model):
        mock_q = MagicMock()
        if model is Alert:
            mock_q.filter.return_value.first.return_value = None
        elif model is FloodPoint:
            mock_q.filter.return_value.first.return_value = mock_kaligawe
        return mock_q

    mock_db_pred.query.side_effect = mock_query_pred_side_effect

    # Jalankan predictive engine dengan force_trigger=True untuk simulasi hujan lebat hulu
    pred_res = asyncio.run(run_predictive_flood_engine(mock_db_pred, force_trigger=True))
    print("-> Predictive engine result:", pred_res)

    assert pred_res["status"] == "alert_active"
    assert pred_res["is_heavy_upstream"] == True
    assert pred_res["lead_time"] == "2-3 jam"
    assert mock_kaligawe.status == "watch"
    assert mock_db_pred.add.called
    print("✅ Predictive flood early warning test passed.")

    print("\n==================================================")
    print("🎉 ALL SCHEDULER & PREDICTIVE TESTS PASSED (100% OK)!")
    print("==================================================")

if __name__ == "__main__":
    test_scheduler_and_predictive()

