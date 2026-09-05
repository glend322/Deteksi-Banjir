"""
Evacuation Finder — Titik Evakuasi Terdekat

Finds the nearest active evacuation point from user's current location.
"""
import math
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvacuationPoint:
    id: str
    name: str
    lat: float
    lng: float
    capacity: str
    supplies: str
    contact: str
    status: str


EVACUATION_POINTS = [
    EvacuationPoint(
        id="eva-1",
        name="Posko Utama Evakuasi Masjid Agung Jawa Tengah (MAJT)",
        lat=-6.9837, lng=110.4455,
        capacity="1.200 jiwa",
        supplies="Dapur umum, medis, genset",
        contact="024-6725455",
        status="Siap Siaga",
    ),
    EvacuationPoint(
        id="eva-2",
        name="Posko Pengungsian Kantor Camat Genuk",
        lat=-6.9628, lng=110.4705,
        capacity="450 jiwa",
        supplies="Obat-obatan dasar, perahu karet BPBD",
        contact="024-6582103",
        status="Aktif Penuh",
    ),
    EvacuationPoint(
        id="eva-3",
        name="RS Islam Sultan Agung (Layanan Gawat Darurat)",
        lat=-6.9560, lng=110.4610,
        capacity="UGD 24 Jam Siaga Perahu Evakuasi",
        supplies="Ambulans amfibi, tabung oksigen",
        contact="024-6580019",
        status="Akses Terbatas via Truk",
    ),
    EvacuationPoint(
        id="eva-4",
        name="Posko BPBD Kota Semarang",
        lat=-6.9900, lng=110.4200,
        capacity="500 jiwa",
        supplies="Tenda, logistik, perahu karet",
        contact="024-3580007",
        status="Siap Siaga",
    ),
    EvacuationPoint(
        id="eva-5",
        name="Kantor SAR / Basarnas Semarang",
        lat=-6.9750, lng=110.4100,
        capacity="Tim SAR Siaga 24 Jam",
        supplies="Perahu motor, alat selam, tenda",
        contact="024-7607777",
        status="Siap Siaga",
    ),
]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_evacuation(
    user_lat: float,
    user_lng: float,
    active_only: bool = True,
) -> dict | None:
    """
    Find the nearest evacuation point from user location.

    Returns dict with id, name, lat, lng, distance_km, duration_walk, or None.
    """
    best_dist = float("inf")
    best_point = None

    for point in EVACUATION_POINTS:
        if active_only and point.status not in ("Siap Siaga", "Aktif Penuh"):
            continue

        dist = _haversine(user_lat, user_lng, point.lat, point.lng)
        if dist < best_dist:
            best_dist = dist
            best_point = point

    if best_point is None:
        return None

    walk_minutes = int(best_dist * 12)

    return {
        "id": best_point.id,
        "name": best_point.name,
        "lat": best_point.lat,
        "lng": best_point.lng,
        "distance_km": round(best_dist, 2),
        "duration_walk": f"{walk_minutes} menit",
        "capacity": best_point.capacity,
        "contact": best_point.contact,
        "status": best_point.status,
    }


def get_all_evacuation_points() -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "lat": p.lat,
            "lng": p.lng,
            "capacity": p.capacity,
            "supplies": p.supplies,
            "contact": p.contact,
            "status": p.status,
        }
        for p in EVACUATION_POINTS
    ]
