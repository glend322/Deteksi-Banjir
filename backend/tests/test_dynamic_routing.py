import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.schemas.routes import RouteLocation
from app.services.routing_service import (
    fetch_osrm_route,
    evaluate_route_flood_risk,
    calculate_safe_routes
)

async def main():
    print("==================================================")
    print("🚦 RUNNING DYNAMIC SAFE ROUTING (OSRM + POSTGIS) TESTS")
    print("==================================================")

    # 1. Test Fetch OSRM Route
    print("\n[TEST 1] Testing OSRM Public Driving Endpoint...")
    origin_coords = (-7.0505, 110.4410) # Banyumanik / Tembalang
    dest_coords = (-6.9644, 110.4281)   # Stasiun Tawang / Semarang Utara
    
    osrm_routes = await fetch_osrm_route([origin_coords, dest_coords], alternatives=True)
    print(f"-> OSRM returned {len(osrm_routes)} candidate routes.")
    if osrm_routes:
        print(f"   Route 1 Distance: {osrm_routes[0]['distance_m']:.0f}m, Duration: {osrm_routes[0]['duration_sec']:.0f}s, Path points: {len(osrm_routes[0]['path'])}")
    else:
        print("   (Note: OSRM public server fallback will be used if network is sandboxed)")

    # 2. Test calculate_safe_routes with Database Session
    db = SessionLocal()
    try:
        print("\n[TEST 2] Testing calculate_safe_routes for MOTOR (vehicle_max_depth_cm = 20)...")
        origin_loc = RouteLocation(lat=-7.0505, lng=110.4410, name="Banyumanik")
        dest_loc = RouteLocation(lat=-6.9644, lng=110.4281, name="Stasiun Tawang")

        res_motor = await calculate_safe_routes(
            origin=origin_loc,
            destination=dest_loc,
            vehicle_type="Motor Bebek",
            vehicle_max_depth_cm=20,
            db=db
        )

        print(f"-> Engine: {res_motor.engine}")
        print(f"-> Total route options: {len(res_motor.options)}")
        for opt in res_motor.options:
            print(f"   * [{opt.type.upper()}] {opt.title} ({opt.badge}) | Duration: {opt.duration} | Dist: {opt.distance}")
            print(f"     Risk: {opt.risk_level} | Avoided: {opt.flood_avoided} | Safe for vehicle: {opt.is_vehicle_safe} | Max depth: {opt.max_depth_cm}cm")

        print("\n[TEST 3] Testing calculate_safe_routes for MOBIL SUV (vehicle_max_depth_cm = 50)...")
        res_suv = await calculate_safe_routes(
            origin=origin_loc,
            destination=dest_loc,
            vehicle_type="Mobil SUV",
            vehicle_max_depth_cm=50,
            db=db
        )
        for opt in res_suv.options:
            print(f"   * [{opt.type.upper()}] {opt.title} ({opt.badge}) | Safe for SUV: {opt.is_vehicle_safe}")

        print("\n==================================================")
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("==================================================")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

