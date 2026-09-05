import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models.user import User, TripHistory
from app.models.flood import FloodPoint, EvacuationPoint
from app.schemas.user import (
    TripHistoryCreate,
    TripHistoryResponse,
    ProximityCheckRequest,
    ProximityCheckResponse
)
from app.api.endpoints.users import (
    save_trip_history,
    get_user_trip_history,
    check_user_proximity_hazard
)

def test_personalization_and_proximity():
    print("==================================================")
    print("👤 RUNNING PERSONALIZATION & PROXIMITY TESTS")
    print("==================================================")

    # 1. Test Trip History Serialization & Endpoint
    print("\n[TEST 1] Testing Trip History CRUD...")
    mock_user = User(id=1, email="andi.pratama@gmail.com", full_name="Andi Pratama")
    
    trip_payload = TripHistoryCreate(
        origin_name="Banyumanik",
        destination_name="Stasiun Tawang",
        duration_str="18 menit",
        distance_km=15.2,
        route_type="Rute Teraman",
        status="Berhasil Menghindari 3 Area Banjir"
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        TripHistory(
            id=1,
            user_id=mock_user.id,
            origin_name=trip_payload.origin_name,
            destination_name=trip_payload.destination_name,
            duration_str=trip_payload.duration_str,
            distance_km=trip_payload.distance_km,
            route_type=trip_payload.route_type,
            status=trip_payload.status,
            created_at=datetime.now(timezone.utc)
        )
    ]

    saved_trip = save_trip_history(trip_payload, mock_user, mock_db)
    assert saved_trip.origin_name == "Banyumanik"
    assert saved_trip.user_id == 1
    assert mock_db.add.called
    print("-> Successfully saved trip history.")

    trips_list = get_user_trip_history(20, mock_user, mock_db)
    assert len(trips_list) == 1
    assert trips_list[0].destination_name == "Stasiun Tawang"
    print("✅ Trip history CRUD test passed.")

    # 2. Test Proximity Risk Warning (User dekat titik Kaligawe 60cm -> CRITICAL)
    print("\n[TEST 2] Testing Proximity Geo-Alert (Danger Zone Near Kaligawe)...")
    
    class MockHazardRecord:
        id = 1
        name = "Jl. Kaligawe Raya"
        depth_cm = 60
        status = "impassable"
        status_label = "Tidak Dapat Dilalui"
        recommendation = "Hindari rute ini, gunakan Tol Gayamsari."
        distance_m = 250.0 # 250 meter dari user

    class MockEvacRecord:
        id = 1
        name = "Posko Utama MAJT"
        capacity = "1.200 jiwa"
        supplies = "Medis, dapur umum, tenda"
        contact = "024-3580007"
        distance_m = 750.0 # 750 meter dari user

    mock_db_prox = MagicMock()
    def mock_query_prox_side_effect(*args):
        mock_q = MagicMock()
        # Jika query FloodPoint
        if len(args) > 0 and args[0] == FloodPoint.id:
            mock_q.filter.return_value.order_by.return_value.first.return_value = MockHazardRecord()
        else: # Query EvacuationPoint
            mock_q.order_by.return_value.first.return_value = MockEvacRecord()
        return mock_q

    mock_db_prox.query.side_effect = mock_query_prox_side_effect

    # User motor (max depth 20 cm) berada di dekat Kaligawe (-6.9540, 110.4560)
    req_danger = ProximityCheckRequest(
        lat=-6.9540,
        lng=110.4560,
        vehicle_max_depth_cm=20
    )
    prox_res = check_user_proximity_hazard(req_danger, mock_db_prox)

    print("-> Proximity Result:", prox_res.danger_level)
    print("-> Warning Message:", prox_res.warning_message)
    print("-> Recommended Action:", prox_res.recommended_action)
    print("-> Nearest Evacuation:", prox_res.nearest_evacuation.name, f"({prox_res.nearest_evacuation.distance_meters}m)")

    assert prox_res.is_in_danger_zone == True
    assert prox_res.danger_level == "CRITICAL"
    assert "Jl. Kaligawe Raya" in prox_res.warning_message
    assert prox_res.nearest_evacuation.name == "Posko Utama MAJT"
    print("✅ Danger zone proximity alert test passed.")

    # 3. Test Proximity Safe Zone (User di area aman Simpang Lima)
    print("\n[TEST 3] Testing Proximity Geo-Alert (Safe Zone in Simpang Lima)...")
    
    class MockFarHazardRecord:
        id = 1
        name = "Jl. Kaligawe Raya"
        depth_cm = 60
        status = "impassable"
        status_label = "Tidak Dapat Dilalui"
        recommendation = "Hindari rute ini."
        distance_m = 4500.0 # 4.5 km (jauh)

    def mock_query_safe_side_effect(*args):
        mock_q = MagicMock()
        if len(args) > 0 and args[0] == FloodPoint.id:
            mock_q.filter.return_value.order_by.return_value.first.return_value = MockFarHazardRecord()
        else:
            mock_q.order_by.return_value.first.return_value = MockEvacRecord()
        return mock_q

    mock_db_prox.query.side_effect = mock_query_safe_side_effect

    req_safe = ProximityCheckRequest(
        lat=-6.9904,
        lng=110.4229,
        vehicle_max_depth_cm=30
    )
    safe_res = check_user_proximity_hazard(req_safe, mock_db_prox)

    print("-> Proximity Result:", safe_res.danger_level)
    print("-> Warning Message:", safe_res.warning_message)

    assert safe_res.is_in_danger_zone == False
    assert safe_res.danger_level == "SAFE"
    print("✅ Safe zone proximity test passed.")

    print("\n==================================================")
    print("🎉 ALL PERSONALIZATION & PROXIMITY TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_personalization_and_proximity()

