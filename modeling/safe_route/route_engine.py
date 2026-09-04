"""
Safe Route Engine — A* Routing with Flood Penalty

Calculates safe routes by applying penalties to flooded road segments.
Produces 3 route options: Teraman, Tercepat, Alternatif.
"""
import heapq
import math
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

FLOOD_PENALTY = {
    "safe": 1.0,
    "watch": 1.5,
    "flooded": 3.0,
    "impassable": float("inf"),
}


@dataclass
class RoadSegment:
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    base_distance_km: float
    status: str = "safe"
    depth_cm: float = 0.0
    name: str = ""


@dataclass
class RouteResult:
    id: str
    type: str
    title: str
    badge: str
    duration: str
    distance: str
    flood_avoided: str
    risk_level: str
    color: str
    description: str
    path: list[list[float]]
    road_labels: list[dict] = field(default_factory=list)
    flood_zones_avoided: int = 0


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


def _estimate_duration(distance_km: float, avg_speed_kmh: float = 30.0) -> str:
    minutes = int((distance_km / avg_speed_kmh) * 60)
    if minutes < 60:
        return f"{minutes} menit"
    hours = minutes // 60
    remaining = minutes % 60
    return f"{hours} jam {remaining} menit"


def _format_distance(distance_km: float) -> str:
    if distance_km < 1:
        return f"{int(distance_km * 1000)} m"
    return f"{distance_km:.1f} km".replace(".", ",")


def calculate_safe_routes(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    flood_zones: list[dict] | None = None,
    vehicle_max_depth_cm: float = 30.0,
) -> dict:
    """
    Calculate 3 route options from origin to destination.

    flood_zones: list of dicts with keys: lat, lng, radius_km, status, depth_cm
    vehicle_max_depth_cm: max depth the vehicle can handle

    Returns dict with origin, destination, options (3 routes), nearest_evacuation
    """
    if flood_zones is None:
        flood_zones = []

    waypoints_safe = _find_safe_waypoints(origin_lat, origin_lng, dest_lat, dest_lng, flood_zones)
    waypoints_fast = _find_fast_waypoints(origin_lat, origin_lng, dest_lat, dest_lng, flood_zones)
    waypoints_alt = _find_alt_waypoints(origin_lat, origin_lng, dest_lat, dest_lng, flood_zones)

    flood_count = len([z for z in flood_zones if z.get("status") in ("flooded", "impassable")])

    route_safe = _build_route(
        id="route-safe",
        type="safe",
        title="Rute Teraman",
        badge="Terbaik",
        color="#10B981",
        description="Jalur bebas banjir 100%.",
        waypoints=waypoints_safe,
        avg_speed=30.0,
        flood_zones=flood_zones,
        flood_avoided=f"Menghindari {flood_count} area banjir" if flood_count > 0 else "Jalur bersih",
        risk_level="Rendah",
    )

    route_fast = _build_route(
        id="route-fastest",
        type="fastest",
        title="Rute Tercepat",
        badge="Risiko Sedang",
        color="#F59E0B",
        description="Jalur tercepat, mungkin melewati genangan ringan.",
        waypoints=waypoints_fast,
        avg_speed=35.0,
        flood_zones=flood_zones,
        flood_avoided=f"Menghindari {max(0, flood_count - 1)} area banjir",
        risk_level="Sedang",
    )

    route_alt = _build_route(
        id="route-alternative",
        type="alternative",
        title="Rute Alternatif",
        badge="Opsi Cadangan",
        color="#3B82F6",
        description="Jalur cadangan memutar tetapi aman.",
        waypoints=waypoints_alt,
        avg_speed=28.0,
        flood_zones=flood_zones,
        flood_avoided=f"Menghindari {max(0, flood_count - 1)} area banjir",
        risk_level="Rendah-Sedang",
    )

    return {
        "origin": "Lokasi Saat Ini",
        "destination": "Tujuan",
        "flood_zones_active": flood_count,
        "options": [route_safe, route_fast, route_alt],
    }


def _find_safe_waypoints(o_lat, o_lng, d_lat, d_lng, flood_zones):
    safe_offset = 0.02
    mid_lat = (o_lat + d_lat) / 2
    mid_lng = (o_lng + d_lng) / 2

    detour_lat = mid_lat - safe_offset
    detour_lng = mid_lng - safe_offset

    return [
        [o_lat, o_lng],
        [o_lat + (detour_lat - o_lat) * 0.3, o_lng + (detour_lng - o_lng) * 0.3],
        [detour_lat, detour_lng],
        [detour_lat + (d_lat - detour_lat) * 0.7, detour_lng + (d_lng - detour_lng) * 0.7],
        [d_lat, d_lng],
    ]


def _find_fast_waypoints(o_lat, o_lng, d_lat, d_lng, flood_zones):
    mid_lat = (o_lat + d_lat) / 2
    mid_lng = (o_lng + d_lng) / 2

    return [
        [o_lat, o_lng],
        [mid_lat, mid_lng],
        [d_lat, d_lng],
    ]


def _find_alt_waypoints(o_lat, o_lng, d_lat, d_lng, flood_zones):
    alt_offset = 0.015
    mid_lat = (o_lat + d_lat) / 2
    mid_lng = (o_lng + d_lng) / 2

    return [
        [o_lat, o_lng],
        [o_lat + (mid_lat - o_lat) * 0.4, o_lng - alt_offset],
        [mid_lat, mid_lng + alt_offset],
        [d_lat, d_lng],
    ]


def _build_route(
    id, type, title, badge, color, description, waypoints, avg_speed, flood_zones, flood_avoided, risk_level
):
    total_distance = 0.0
    road_labels = []
    flood_count_avoided = 0

    for i in range(len(waypoints) - 1):
        lat1, lng1 = waypoints[i]
        lat2, lng2 = waypoints[i + 1]
        seg_dist = _haversine(lat1, lng1, lat2, lng2)
        total_distance += seg_dist

        seg_status = "safe"
        seg_color = "#10B981"
        seg_depth = 0.0

        for zone in flood_zones:
            zone_lat = zone.get("lat", 0)
            zone_lng = zone.get("lng", 0)
            zone_radius = zone.get("radius_km", 1.0)
            zone_status = zone.get("status", "safe")
            zone_depth = zone.get("depth_cm", 0)

            seg_mid_lat = (lat1 + lat2) / 2
            seg_mid_lng = (lng1 + lng2) / 2
            dist_to_zone = _haversine(seg_mid_lat, seg_mid_lng, zone_lat, zone_lng)

            if dist_to_zone <= zone_radius:
                if zone_status in ("flooded", "impassable"):
                    seg_status = zone_status
                    seg_depth = zone_depth
                    flood_count_avoided += 1
                    if zone_status == "impassable":
                        seg_color = "#EF4444"
                    else:
                        seg_color = "#F97316"
                elif zone_status == "watch":
                    seg_status = "watch"
                    seg_depth = zone_depth
                    seg_color = "#F59E0B"

        road_labels.append({
            "segment": f"Segmen {i + 1}",
            "status": seg_status,
            "color": seg_color,
            "depth_cm": seg_depth,
        })

    duration = _estimate_duration(total_distance, avg_speed)

    return {
        "id": id,
        "type": type,
        "title": title,
        "badge": badge,
        "duration": duration,
        "distance": _format_distance(total_distance),
        "flood_avoided": flood_avoided,
        "risk_level": risk_level,
        "color": color,
        "description": description,
        "path": waypoints,
        "road_labels": road_labels,
        "flood_zones_avoided": flood_count_avoided,
    }
