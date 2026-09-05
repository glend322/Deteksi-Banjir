import asyncio
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.schemas.routes import RouteLocation, RouteCalculateResponse
from app.services.routing_service import (
    evaluate_route_flood_risk,
    generate_corridor_fallback_route,
    calculate_safe_routes,
    format_duration,
    format_distance
)

class MockFloodPoint:
    def __init__(self, id, name, status, depth_cm, lat, lng):
        self.id = id
        self.name = name
        self.status = status
        self.depth_cm = depth_cm
        self.lat = lat
        self.lng = lng

class MockFloodZone:
    def __init__(self, id, name, status, geom=None):
        self.id = id
        self.name = name
        self.status = status
        self.geom = geom

def test_unit_routing():
    print("==================================================")
    print("🚦 RUNNING UNIT TESTS FOR DYNAMIC SAFE ROUTING")
    print("==================================================")

    # 1. Test formatters
    print("\n[TEST 1] Testing Duration and Distance Formatters...")
    assert format_duration(120) == "2 menit", f"Expected '2 menit', got {format_duration(120)}"
    assert format_duration(3660) == "1 jam 1 menit", f"Expected '1 jam 1 menit', got {format_duration(3660)}"
    assert format_distance(12400) == "12,4 km", f"Expected '12,4 km', got {format_distance(12400)}"
    print("✅ Formatters test passed.")

    # 2. Test Flood Risk Evaluation
    print("\n[TEST 2] Testing Spatial Flood Risk Evaluation (Motor vs SUV)...")
    flood_points = [
        MockFloodPoint(1, "Jl. Kaligawe Raya", "impassable", 60, -6.9535, 110.4570),
        MockFloodPoint(2, "Simpang Gayamsari", "watch", 15, -6.9940, 110.4530),
    ]
    flood_zones = []

    # Path 1: Melewati Gayamsari (dekat -6.9940, 110.4530)
    path_near_gayamsari = [
        [-7.0505, 110.4410],
        [-6.9940, 110.4530],
        [-6.9644, 110.4281]
    ]

    # Evaluasi untuk Motor (max 20 cm) -> Genangan 15 cm masih aman (<= 20 cm)
    eval_motor = evaluate_route_flood_risk(path_near_gayamsari, flood_points, flood_zones, vehicle_max_depth_cm=20)
    print("Eval Motor on Gayamsari:", eval_motor)
    assert eval_motor["is_vehicle_safe"] == True
    assert "Simpang Gayamsari" in eval_motor["intersected_points"]
    assert eval_motor["max_depth_cm"] == 15

    # Path 2: Melewati Kaligawe (-6.9535, 110.4570) dengan kedalaman 60 cm
    path_near_kaligawe = [
        [-7.0000, 110.4400],
        [-6.9535, 110.4570],
        [-6.9400, 110.4600]
    ]
    eval_kaligawe_motor = evaluate_route_flood_risk(path_near_kaligawe, flood_points, flood_zones, vehicle_max_depth_cm=20)
    print("Eval Motor on Kaligawe (60cm):", eval_kaligawe_motor)
    assert eval_kaligawe_motor["is_vehicle_safe"] == False
    assert eval_kaligawe_motor["max_depth_cm"] == 60
    assert "Jl. Kaligawe Raya" in eval_kaligawe_motor["intersected_points"]

    print("✅ Spatial flood risk evaluation test passed.")

    # 3. Test Fallback Corridor Route Generation
    print("\n[TEST 3] Testing Fallback Route Corridors...")
    fb_safe = generate_corridor_fallback_route((-7.0505, 110.4410), (-6.9644, 110.4281), "safe")
    fb_fastest = generate_corridor_fallback_route((-7.0505, 110.4410), (-6.9644, 110.4281), "fastest")
    fb_alt = generate_corridor_fallback_route((-7.0505, 110.4410), (-6.9644, 110.4281), "alternative")

    assert len(fb_safe["path"]) >= 4
    assert fb_fastest["duration_sec"] < fb_safe["duration_sec"]
    print(f"Fallback safe duration: {fb_safe['duration_sec']}s, fastest: {fb_fastest['duration_sec']}s")
    print("✅ Fallback route corridors test passed.")

    # 4. Test calculate_safe_routes with Mock DB Session
    print("\n[TEST 4] Testing calculate_safe_routes end-to-end with Mock Session...")
    mock_db = MagicMock()
    mock_db.query.return_value.all.side_effect = [
        flood_points, # query FloodPoint
        flood_zones   # query FloodZone
    ]

    async def run_async_calc():
        resp = await calculate_safe_routes(
            origin=RouteLocation(lat=-7.0505, lng=110.4410, name="Banyumanik"),
            destination=RouteLocation(lat=-6.9644, lng=110.4281, name="Stasiun Tawang"),
            vehicle_type="Motor Bebek",
            vehicle_max_depth_cm=20,
            db=mock_db
        )
        return resp

    resp = asyncio.run(run_async_calc())
    assert isinstance(resp, RouteCalculateResponse)
    assert len(resp.options) == 3
    print(f"Engine: {resp.engine}")
    for opt in resp.options:
        print(f"Option: [{opt.type}] {opt.title} | {opt.duration} | {opt.distance} | Badge: {opt.badge}")
        # Test serialization of camelCase aliases
        dump = opt.model_dump(by_alias=True)
        assert "floodAvoided" in dump
        assert "riskLevel" in dump

    print("\n==================================================")
    print("🎉 ALL UNIT TESTS PASSED SUCCESSFULLY (100% OK)!")
    print("==================================================")

if __name__ == "__main__":
    test_unit_routing()
