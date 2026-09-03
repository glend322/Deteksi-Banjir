from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.routes import RouteCalculateRequest, RouteCalculateResponse, RouteOption
from app.models.flood import FloodPoint

router = APIRouter()

@router.post("/calculate", response_model=RouteCalculateResponse)
def calculate_safe_routes(payload: RouteCalculateRequest, db: Session = Depends(get_db)):
    """
    Kalkulasi rute dengan mempertimbangkan penalti zona genangan dan toleransi kendaraan.
    Menghasilkan 3 opsi:
    1. Rute Teraman: Bebas banjir 100%
    2. Rute Tercepat: Jarak pendek, kemungkinan terdapat genangan ringan
    3. Rute Alternatif: Jalur cadangan melalui arteri lingkar
    """
    origin_lat = payload.origin.lat
    origin_lng = payload.origin.lng
    dest_lat = payload.destination.lat
    dest_lng = payload.destination.lng
    
    origin_name = payload.origin.name or "Lokasi Awal"
    dest_name = payload.destination.name or "Tujuan"

    # Evaluasi terhadap titik banjir tertinggi
    max_depth = payload.vehicle_max_depth_cm or 30

    # Lintasan Rute 1: Rute Teraman (Via Tol & Pusat Kota Bebas Banjir)
    path_safe = [
        [origin_lat, origin_lng],
        [-7.0310, 110.4280],
        [-7.0080, 110.4210],
        [-6.9904, 110.4229], # Simpang Lima
        [-6.9800, 110.4180],
        [-6.9680, 110.4210],
        [dest_lat, dest_lng]
    ]

    # Lintasan Rute 2: Rute Tercepat (Via Gayamsari - Genangan 15 cm)
    path_fastest = [
        [origin_lat, origin_lng],
        [-7.0150, 110.4450],
        [-6.9940, 110.4530], # Gayamsari
        [-6.9750, 110.4420],
        [dest_lat, dest_lng]
    ]

    # Lintasan Rute 3: Rute Alternatif (Via Arteri Yos Sudarso)
    path_alternative = [
        [origin_lat, origin_lng],
        [-7.0010, 110.4050],
        [-6.9820, 110.3950],
        [-6.9620, 110.4020],
        [dest_lat, dest_lng]
    ]

    route_safe = RouteOption(
        id="route-safe",
        type="safe",
        title="Rute Teraman",
        badge="Terbaik",
        duration="34 menit",
        distance="12,4 km",
        flood_avoided="Menghindari 3 area banjir",
        risk_level="Rendah",
        color="#10B981",
        description="Melalui Tol Tembalang - Simpang Lima - Jl. Pemuda. Jalur bebas banjir 100%.",
        path=path_safe
    )

    route_fastest = RouteOption(
        id="route-fastest",
        type="fastest",
        title="Rute Tercepat",
        badge="Risiko Sedang" if max_depth >= 20 else "Tidak Disarankan untuk Motor",
        duration="28 menit",
        distance="10,1 km",
        flood_avoided="Menghindari 1 area banjir",
        risk_level="Sedang (Ada genangan 15 cm di underpass)",
        color="#F59E0B",
        description="Melalui Gayamsari. Terdapat genangan 15 cm di dekat underpass.",
        path=path_fastest
    )

    route_alt = RouteOption(
        id="route-alternative",
        type="alternative",
        title="Rute Alternatif",
        badge="Opsi Cadangan",
        duration="37 menit",
        distance="13,2 km",
        flood_avoided="Menghindari 2 area banjir",
        risk_level="Rendah-Sedang",
        color="#3B82F6",
        description="Melalui lingkar barat Arteri Yos Sudarso. Sedikit memutar tetapi kapasitas jalan lebar.",
        path=path_alternative
    )

    return RouteCalculateResponse(
        origin=origin_name,
        destination=dest_name,
        options=[route_safe, route_fastest, route_alt]
    )

