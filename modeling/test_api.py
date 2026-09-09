"""Test FastAPI endpoints via TestClient."""
import sys
sys.path.insert(0, ".")

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health():
    r = client.get("/health")
    print("GET /health:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_flood_zones():
    r = client.get("/api/flood-zones")
    print("GET /api/flood-zones:", r.status_code)
    assert r.status_code == 200

def test_evacuation_points():
    r = client.get("/api/evacuation-points")
    print("GET /api/evacuation-points:", r.status_code, "count:", len(r.json()))
    assert r.status_code == 200
    assert len(r.json()) == 5

def test_calculate_route():
    route_req = {
        "origin": {"lat": -7.0505, "lng": 110.4410, "name": "Tembalang"},
        "destination": {"lat": -6.9644, "lng": 110.4281, "name": "Stasiun Tawang"},
        "vehicle_max_depth_cm": 30.0
    }
    r = client.post("/api/calculate-route", json=route_req)
    print("POST /api/calculate-route:", r.status_code)
    data = r.json()
    print("  Routes:", len(data.get("options", [])))
    for opt in data.get("options", []):
        print("   ", opt["title"], ":", opt["distance"], "|", opt["duration"])
    evac = data.get("nearest_evacuation")
    if evac:
        print("  Evacuation:", evac["name"])
    assert r.status_code == 200
    assert len(data["options"]) == 3

if __name__ == "__main__":
    tests = [test_health, test_flood_zones, test_evacuation_points, test_calculate_route]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print("  [FAIL]", t.__name__, ":", e)
            failed += 1
    print("=" * 50)
    print("Results:", passed, "passed,", failed, "failed out of", len(tests))
    if failed == 0:
        print("All API endpoints working!")
    else:
        sys.exit(1)
