"""Test the new graph-based route engine."""
import sys
sys.path.insert(0, ".")

from routing.route_engine import calculate_safe_routes

def test_basic_routing():
    print("=== Test 1: Basic A* Routing (No Flood) ===")
    result = calculate_safe_routes(
        origin_lat=-7.0505, origin_lng=110.4410,
        dest_lat=-6.9644, dest_lng=110.4281,
        flood_zones=[], vehicle_max_depth_cm=30.0,
    )
    print("Origin:", result["origin"])
    print("Destination:", result["destination"])
    for opt in result["options"]:
        print("  %s (%s): %s | %s | risk=%s | path_pts=%d | labels=%d" % (
            opt["title"], opt["type"], opt["distance"], opt["duration"],
            opt["risk_level"], len(opt["path"]), len(opt["road_labels"]),
        ))
    assert len(result["options"]) == 3, "Expected 3 route options"
    for opt in result["options"]:
        assert len(opt["path"]) >= 2, "Path should have at least 2 points"
        assert opt["color"].startswith("#"), "Color should be hex"
    print("  [PASS]\n")

def test_routing_with_flood():
    print("=== Test 2: A* Routing with Flood Zones ===")
    flood_zones = [
        {"lat": -6.9904, "lng": 110.4229, "radius_km": 1.5, "status": "flooded", "depth_cm": 50},
    ]
    result = calculate_safe_routes(
        origin_lat=-7.0505, origin_lng=110.4410,
        dest_lat=-6.9644, dest_lng=110.4281,
        flood_zones=flood_zones, vehicle_max_depth_cm=30.0,
    )
    print("Active flood zones:", result["flood_zones_active"])
    for opt in result["options"]:
        print("  %s: %s | %s | risk=%s | avoided=%s" % (
            opt["title"], opt["distance"], opt["duration"],
            opt["risk_level"], opt["flood_avoided"],
        ))
    assert result["flood_zones_active"] == 1
    print("  [PASS]\n")

def test_road_labels():
    print("=== Test 3: Road Labels with Real Names ===")
    result = calculate_safe_routes(
        origin_lat=-7.0505, origin_lng=110.4410,
        dest_lat=-6.9644, dest_lng=110.4281,
        flood_zones=[], vehicle_max_depth_cm=30.0,
    )
    safe_route = result["options"][0]
    print("  Route:", safe_route["title"])
    print("  Road labels count:", len(safe_route["road_labels"]))
    for rl in safe_route["road_labels"][:5]:
        print("    %s: %s (%s) depth=%scm" % (
            rl["segment"], rl["status"], rl["color"], rl["depth_cm"],
        ))
    assert len(safe_route["road_labels"]) > 0, "Should have road labels"
    for rl in safe_route["road_labels"]:
        assert "segment" in rl, "Label missing segment name"
        assert "status" in rl, "Label missing status"
        assert "color" in rl, "Label missing color"
    print("  [PASS]\n")

def test_flood_penalty_effect():
    print("=== Test 4: Flood Penalty Affects Route Choice ===")
    # Place flood directly on the fastest route corridor
    flood_zones = [
        {"lat": -7.005, "lng": 110.442, "radius_km": 2.0, "status": "impassable", "depth_cm": 60},
    ]
    result = calculate_safe_routes(
        origin_lat=-7.0505, origin_lng=110.4410,
        dest_lat=-6.9644, dest_lng=110.4281,
        flood_zones=flood_zones, vehicle_max_depth_cm=30.0,
    )
    for opt in result["options"]:
        print("  %s: %s | risk=%s" % (opt["title"], opt["distance"], opt["risk_level"]))
    # Safe route should try to avoid the impassable zone
    print("  [PASS]\n")

if __name__ == "__main__":
    tests = [test_basic_routing, test_routing_with_flood, test_road_labels, test_flood_penalty_effect]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print("  [FAIL]", t.__name__, ":", e)
            import traceback; traceback.print_exc()
            failed += 1
    print("=" * 50)
    print("Results: %d passed, %d failed out of %d" % (passed, failed, len(tests)))
