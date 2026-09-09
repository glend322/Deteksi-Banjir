"""Full pipeline test — routing, area mapping, evacuation, classifier integration."""
import sys
sys.path.insert(0, ".")

from routing.route_engine import calculate_safe_routes
from routing.evacuation_finder import find_nearest_evacuation, get_all_evacuation_points
from routing.area_mapping import get_area_name, get_area_detail


def test_area_mapping():
    print("=== Testing Area Mapping ===")
    r1 = get_area_name(-6.9535, 110.4570)
    r2 = get_area_name(-6.9620, 110.4735)
    r3 = get_area_name(-6.9904, 110.4229)
    print("  Kaligawe:", r1)
    print("  Genuk:", r2)
    print("  Simpang Lima:", r3)
    d = get_area_detail(-6.9535, 110.4570)
    print("  Detail:", d)
    assert "Genuk" in r1 or "Trimulyo" in r1, f"Expected Genuk/Trimulyo area, got {r1}"
    assert "Genuk" in r2 or "Genuk" in r2, f"Expected Genuk area, got {r2}"
    print("  [PASS] Area mapping works\n")


def test_evacuation_finder():
    print("=== Testing Evacuation Finder ===")
    evac = find_nearest_evacuation(-6.9535, 110.4570)
    assert evac is not None, "Expected an evacuation point"
    print("  Nearest:", evac["name"])
    print("  Distance:", evac["distance_km"], "km")
    print("  Walk:", evac["duration_walk"])
    assert evac["distance_km"] > 0, "Distance should be positive"
    assert "menit" in evac["duration_walk"], "Duration should contain 'menit'"

    all_pts = get_all_evacuation_points()
    print("  Total evacuation points:", len(all_pts))
    assert len(all_pts) == 5, f"Expected 5 evacuation points, got {len(all_pts)}"
    print("  [PASS] Evacuation finder works\n")


def test_route_engine():
    print("=== Testing Route Engine ===")
    flood_zones = [
        {"lat": -6.9535, "lng": 110.4570, "radius_km": 1.0, "status": "flooded", "depth_cm": 50},
        {"lat": -6.9620, "lng": 110.4735, "radius_km": 0.5, "status": "watch", "depth_cm": 15},
    ]
    result = calculate_safe_routes(
        origin_lat=-7.0505, origin_lng=110.4410,
        dest_lat=-6.9644, dest_lng=110.4281,
        flood_zones=flood_zones,
        vehicle_max_depth_cm=30.0,
    )
    print("  Origin:", result["origin"])
    print("  Destination:", result["destination"])
    print("  Active flood zones:", result["flood_zones_active"])

    assert len(result["options"]) == 3, f"Expected 3 route options, got {len(result['options'])}"
    for opt in result["options"]:
        print("  Route:", opt["title"], "|", opt["distance"], "|", opt["duration"], "| risk:", opt["risk_level"])
        assert "path" in opt, "Route missing 'path'"
        assert len(opt["path"]) >= 2, "Route path should have at least 2 waypoints"
        assert "road_labels" in opt, "Route missing 'road_labels'"
        assert opt["color"].startswith("#"), "Route color should be hex"
    print("  [PASS] Route engine works\n")


def test_full_detection_simulation():
    """Simulate a full detection flow without CCTV (mock)."""
    print("=== Testing Full Detection Simulation ===")
    from detection.classifier import classify_flood
    from detection.cv_model import depth_to_classification, cause_to_text, classification_to_status, classification_to_color

    # Simulate CV output
    depth_cm = 35.0
    cause_probs = {"river": 0.85, "trash": 0.12}

    depth_label = depth_to_classification(depth_cm)
    cause = cause_to_text(cause_probs, threshold=0.5)
    area = get_area_name(-6.9535, 110.4570)

    cls = classify_flood(depth_label, area, cause, river_detected=True, trash_detected=False)

    print("  Depth:", depth_cm, "cm ->", depth_label)
    print("  Cause:", cause)
    print("  Area:", area)
    print("  Notification:", cls.notification)
    print("  Status:", cls.status, "(", cls.status_label, ")")
    print("  Color:", cls.color)

    assert cls.status in ("watch", "flooded", "impassable", "safe")
    assert cls.color.startswith("#")
    assert "banjir" in cls.notification.lower() or cls.status == "safe"
    print("  [PASS] Full detection simulation works\n")


def test_output_contract():
    """Verify output matches frontend SAFEROUTE_DATA contract."""
    print("=== Testing Output Contract ===")
    from detection.classifier import classify_flood

    cls = classify_flood("sedang", "Genuk", "sungai meluap", river_detected=True)
    status_map = {"dangkal": "watch", "sedang": "flooded", "dalam": "impassable"}

    assert cls.status in ("watch", "flooded", "impassable", "safe"), f"Invalid status: {cls.status}"
    assert cls.status_label in ("Waspada", "Tergenang", "Tidak Dapat Dilalui", "Aman"), f"Invalid label: {cls.status_label}"
    assert cls.color in ("#F59E0B", "#F97316", "#EF4444", "#10B981"), f"Invalid color: {cls.color}"
    assert "Daerah" in cls.notification, "Notification must start with 'Daerah'"
    assert "banjir tingkat" in cls.notification, "Notification must contain 'banjir tingkat'"
    assert "Penyebab" in cls.notification, "Notification must contain 'Penyebab'"
    print("  Notification:", cls.notification)
    print("  [PASS] Output contract valid\n")


if __name__ == "__main__":
    tests = [
        test_area_mapping,
        test_evacuation_finder,
        test_route_engine,
        test_full_detection_simulation,
        test_output_contract,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print("  [FAIL]", test.__name__, ":", e)
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed == 0:
        print("All tests passed!")
    else:
        sys.exit(1)
