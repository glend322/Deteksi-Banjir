"""
Area Mapping — Reverse Geocode lat/lng → Nama Daerah Semarang

Maps GPS coordinates to kecamatan/kelurahan names using
a static lookup table of Semarang administrative areas.
"""
import math
from dataclasses import dataclass


@dataclass
class AreaEntry:
    name: str
    kecamatan: str
    kelurahan: str
    lat: float
    lng: float


# Static database of known flood-prone areas in Semarang
SEMARANG_AREAS = [
    AreaEntry("Kaligawe", "Genuk", "Trimulyo", -6.9535, 110.4570),
    AreaEntry("Genuk", "Genuk", "Genuk", -6.9620, 110.4735),
    AreaEntry("Tambakrejo", "Semarang Utara", "Tambakrejo", -6.9450, 110.4350),
    AreaEntry("Mangkang", "Tugu", "Mangkang", -6.9745, 110.3320),
    AreaEntry("Gayamsari", "Gayamsari", "Gayamsari", -6.9940, 110.4530),
    AreaEntry("Simpang Lima", "Semarang Tengah", "Pandansari", -6.9904, 110.4229),
    AreaEntry("Tembalang", "Tembalang", "Tembalang", -7.0505, 110.4410),
    AreaEntry("Banyumanik", "Banyumanik", "Banyumanik", -7.0600, 110.4300),
    AreaEntry("Semarang Utara", "Semarang Utara", "Kuningan", -6.9380, 110.4150),
    AreaEntry("Tugu", "Tugu", "Tugu", -6.9680, 110.3200),
    AreaEntry("Semarang Barat", "Semarang Barat", "Tanjung Emas", -6.9400, 110.3800),
    AreaEntry("Semarang Selatan", "Semarang Selatan", "Brumbungan", -7.0050, 110.4350),
    AreaEntry("Semarang Timur", "Semarang Timur", "Rejomulyo", -6.9850, 110.4450),
    AreaEntry("Ngaliyan", "Ngaliyan", "Ngaliyan", -7.0150, 110.3800),
    AreaEntry("Gajahmungkur", "Gajahmungkur", "Gajahmungkur", -7.0100, 110.4250),
    AreaEntry("Candisari", "Candisari", "Candisari", -7.0200, 110.4500),
    AreaEntry("Tlogosari", "Pedurungan", "Tlogosari", -7.0000, 110.4700),
    AreaEntry("Pedurungan", "Pedurungan", "Pedurungan Kulon", -6.9950, 110.4800),
    AreaEntry("Banjardowo", "Genuk", "Banjardowo", -6.9500, 110.4650),
    AreaEntry("Mijen", "Mijen", "Mijen", -7.0300, 110.3700),
    AreaEntry("Bitingan", "Semarang Utara", "Bitingan", -6.9400, 110.4250),
    AreaEntry("Pudpayaman", "Semarang Utara", "Pudpayaman", -6.9350, 110.4400),
    AreaEntry("Tanjungharjo", "Semarang Utara", "Tanjungharjo", -6.9300, 110.4300),
    AreaEntry("Bandarharjo", "Semarang Utara", "Bandarharjo", -6.9320, 110.4200),
    AreaEntry("Kuningan", "Semarang Utara", "Kuningan", -6.9370, 110.4180),
    AreaEntry("Pelemburan", "Semarang Utara", "Pelemburan", -6.9340, 110.4280),
    AreaEntry("Purwosari", "Semarang Utara", "Purwosari", -6.9390, 110.4320),
    AreaEntry("Samberembe", "Genuk", "Samberembe", -6.9550, 110.4500),
    AreaEntry("Sembungharjo", "Genuk", "Sembungharjo", -6.9480, 110.4600),
    AreaEntry("Karangroto", "Genuk", "Karangroto", -6.9520, 110.4700),
    AreaEntry("Gabus", "Genuk", "Gabus", -6.9580, 110.4800),
    AreaEntry("Trimulyo", "Genuk", "Trimulyo", -6.9540, 110.4550),
    AreaEntry("Wonosari", "Genuk", "Wonosari", -6.9600, 110.4750),
]


def get_area_name(lat: float, lng: float) -> str:
    """
    Get area name (kecamatan, kelurahan) from coordinates.

    Uses closest-point matching from the static database.

    Returns:
        Formatted string: "Kelurahan, Kecamatan" or "Kecamatan, Semarang"
    """
    best_dist = float("inf")
    best_area = None

    for area in SEMARANG_AREAS:
        d = _haversine(lat, lng, area.lat, area.lng)
        if d < best_dist:
            best_dist = d
            best_area = area

    if best_area is None:
        return "Semarang"

    if best_dist < 1.0:
        return f"{best_area.kelurahan}, {best_area.kecamatan}"
    elif best_dist < 3.0:
        return best_area.kecamatan
    else:
        return "Semarang"


def get_area_detail(lat: float, lng: float) -> dict:
    """
    Get detailed area information from coordinates.

    Returns dict with name, kecamatan, kelurahan, distance_km.
    """
    best_dist = float("inf")
    best_area = None

    for area in SEMARANG_AREAS:
        d = _haversine(lat, lng, area.lat, area.lng)
        if d < best_dist:
            best_dist = d
            best_area = area

    if best_area is None:
        return {"name": "Semarang", "kecamatan": "Semarang", "kelurahan": "", "distance_km": 0}

    return {
        "name": best_area.name,
        "kecamatan": best_area.kecamatan,
        "kelurahan": best_area.kelurahan,
        "distance_km": round(best_dist, 2),
    }


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance in km between two points."""
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
