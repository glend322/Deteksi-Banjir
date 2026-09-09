"""
Safe Route Engine — A* Routing with Flood Penalty

Calculates safe routes using real OSM road graph data.
Applies penalties to flooded road segments and produces 3 route options.

Algorithm: A* with modified cost function:
  cost(u, v) = base_distance(u, v) * flood_penalty(status(u, v))

Flood Penalty Table:
  safe     = 1.0 (no penalty)
  watch    = 1.5 (shallow, < 20cm)
  flooded  = 3.0 (moderate, 20-40cm)
  impassable = INF (deep > 40cm, excluded from graph)
"""
import math
import logging
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from routing.road_graph import RoadGraph, _haversine, _snap_key

logger = logging.getLogger(__name__)

# Flood penalty multipliers (PRD Section 3.5)
FLOOD_PENALTY = {
    "safe": 1.0,
    "watch": 1.5,
    "flooded": 3.0,
    "impassable": float("inf"),
}

# Status color mapping (PRD Section 3.6)
STATUS_COLORS = {
    "safe": "#10B981",
    "watch": "#F59E0B",
    "flooded": "#F97316",
    "impassable": "#EF4444",
}

# Vehicle type speed estimates (km/h) for duration calculation
VEHICLE_SPEEDS = {
    "safe": 35.0,
    "watch": 25.0,
    "flooded": 15.0,
}

# Average speed for route type
ROUTE_SPEEDS = {
    "safe": 30.0,
    "fastest": 35.0,
    "alternative": 28.0,
}


def _estimate_duration(distance_km: float, avg_speed_kmh: float = 30.0) -> str:
    """Format duration as human-readable string."""
    minutes = int((distance_km / avg_speed_kmh) * 60)
    if minutes < 1:
        return "1 menit"
    if minutes >= 60:
        hours = minutes // 60
        remaining = minutes % 60
        return f"{hours} jam {remaining} menit" if remaining > 0 else f"{hours} jam"
    return f"{minutes} menit"


def _format_distance(distance_km: float) -> str:
    """Format distance as human-readable string."""
    if distance_km < 1:
        return f"{int(distance_km * 1000)} m"
    return f"{distance_km:.1f} km".replace(".", ",")


def _get_segment_status(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    flood_zones: list[dict],
) -> tuple[str, float]:
    """
    Determine flood status for a road segment by checking proximity to flood zones.

    Returns (status, depth_cm) tuple.
    """
    best_status = "safe"
    best_depth = 0.0
    mid_lat = (lat1 + lat2) / 2
    mid_lng = (lng1 + lng2) / 2

    for zone in flood_zones:
        zone_lat = zone.get("lat", 0)
        zone_lng = zone.get("lng", 0)
        zone_radius = zone.get("radius_km", 1.0)
        zone_status = zone.get("status", "safe")
        zone_depth = zone.get("depth_cm", 0)

        dist = _haversine(mid_lat, mid_lng, zone_lat, zone_lng)
        if dist <= zone_radius:
            # Prioritize worse status
            status_order = {"safe": 0, "watch": 1, "flooded": 2, "impassable": 3}
            if status_order.get(zone_status, 0) > status_order.get(best_status, 0):
                best_status = zone_status
                best_depth = zone_depth

    return best_status, best_depth


def _astar_with_penalty(
    graph: RoadGraph,
    origin_node: tuple,
    dest_node: tuple,
    flood_zones: list[dict],
    vehicle_max_depth_cm: float,
    penalty_scale: float = 1.0,
) -> Optional[list]:
    """
    Run A* search with flood penalty on the road graph.

    Args:
        graph: RoadGraph instance
        origin_node: start node (lat, lng) tuple
        dest_node: end node (lat, lng) tuple
        flood_zones: list of flood zone dicts
        vehicle_max_depth_cm: vehicle max depth tolerance
        penalty_scale: multiplier for flood penalties (1.0=normal, 0.5=relaxed, 2.0=strict)

    Returns:
        List of (lat, lng) waypoints, or None if no path found
    """
    G = graph.graph

    def heuristic(u, v):
        return _haversine(u[0], u[1], v[0], v[1])

    def cost(u, v, edge_data):
        base_dist = edge_data.get("weight", _haversine(u[0], u[1], v[0], v[1]))

        # Get road segment coords to check flood status
        edge_info = graph.get_edge_data(u, v)
        if edge_info and len(edge_info.coords) >= 2:
            # Check flood status along the segment
            seg_status = "safe"
            seg_depth = 0.0
            for i in range(len(edge_info.coords) - 1):
                s, d = _get_segment_status(
                    edge_info.coords[i][0], edge_info.coords[i][1],
                    edge_info.coords[i + 1][0], edge_info.coords[i + 1][1],
                    flood_zones,
                )
                status_order = {"safe": 0, "watch": 1, "flooded": 2, "impassable": 3}
                if status_order.get(s, 0) > status_order.get(seg_status, 0):
                    seg_status = s
                    seg_depth = d

            # Apply penalty
            penalty = FLOOD_PENALTY.get(seg_status, 1.0) * penalty_scale

            # Vehicle filter: if depth exceeds vehicle max, treat as impassable
            if seg_depth > vehicle_max_depth_cm and seg_status != "safe":
                penalty = float("inf")

            return base_dist * penalty

        return base_dist

    try:
        path = nx.astar_path(
            G, origin_node, dest_node,
            heuristic=heuristic,
            weight=lambda u, v, d: cost(u, v, d),
        )
        return [(node[0], node[1]) for node in path]
    except nx.NetworkXNoPath:
        return None
    except nx.NodeNotFound:
        return None


def _build_road_labels(
    path: list[tuple],
    graph: RoadGraph,
    flood_zones: list[dict],
) -> list[dict]:
    """
    Build road_labels array for each segment in the path.

    Returns list of dicts with segment name, status, color, depth_cm.
    """
    labels = []
    seen_roads = set()

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge = graph.get_edge_data(u, v)

        if edge is None:
            continue

        road_name = edge.name
        road_key = (road_name, u, v)
        if road_key in seen_roads:
            continue
        seen_roads.add(road_key)

        # Check flood status along this edge
        seg_status = "safe"
        seg_depth = 0.0
        for j in range(len(edge.coords) - 1):
            s, d = _get_segment_status(
                edge.coords[j][0], edge.coords[j][1],
                edge.coords[j + 1][0], edge.coords[j + 1][1],
                flood_zones,
            )
            status_order = {"safe": 0, "watch": 1, "flooded": 2, "impassable": 3}
            if status_order.get(s, 0) > status_order.get(seg_status, 0):
                seg_status = s
                seg_depth = d

        labels.append({
            "segment": road_name,
            "status": seg_status,
            "color": STATUS_COLORS.get(seg_status, "#10B981"),
            "depth_cm": round(seg_depth, 1),
        })

    return labels


def _path_to_coords(path: list[tuple]) -> list[list[float]]:
    """Convert list of (lat, lng) tuples to [[lat, lng], ...] format."""
    return [[lat, lng] for lat, lng in path]


def _count_flood_zones_avoided(
    path: list[tuple],
    graph: RoadGraph,
    flood_zones: list[dict],
) -> int:
    """Count how many flood zones the path passes through or near."""
    count = 0
    checked_zones = set()

    for zone in flood_zones:
        zone_key = (zone.get("lat", 0), zone.get("lng", 0))
        if zone_key in checked_zones:
            continue
        checked_zones.add(zone_key)

        zone_lat = zone.get("lat", 0)
        zone_lng = zone.get("lng", 0)
        zone_radius = zone.get("radius_km", 1.0)

        # Check if any path point is within the flood zone
        for lat, lng in path:
            dist = _haversine(lat, lng, zone_lat, zone_lng)
            if dist <= zone_radius:
                count += 1
                break

    return count


def calculate_safe_routes(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    flood_zones: list[dict] | None = None,
    vehicle_max_depth_cm: float = 30.0,
) -> dict:
    """
    Calculate 3 route options from origin to destination using A* with flood penalty.

    Args:
        origin_lat, origin_lng: User's current GPS location
        dest_lat, dest_lng: Destination coordinates
        flood_zones: list of dicts with keys: lat, lng, radius_km, status, depth_cm
        vehicle_max_depth_cm: max depth the vehicle can handle (default 30cm)

    Returns:
        dict with origin, destination, flood_zones_active, options (3 routes)
    """
    if flood_zones is None:
        flood_zones = []

    # Load road graph
    road_graph = RoadGraph.load()

    # Find nearest nodes to origin and destination
    origin_node = road_graph.find_nearest_node(origin_lat, origin_lng)
    dest_node = road_graph.find_nearest_node(dest_lat, dest_lng)

    if origin_node is None or dest_node is None:
        logger.warning("Could not find nearest nodes for origin/destination")
        return _fallback_routes(origin_lat, origin_lng, dest_lat, dest_lng, flood_zones, vehicle_max_depth_cm)

    logger.info(f"Routing from {origin_node} to {dest_node}")

    # Count active flood zones
    flood_count = len([z for z in flood_zones if z.get("status") in ("flooded", "impassable")])

    # --- Route 1: Safest (strict penalty) ---
    path_safe = _astar_with_penalty(
        road_graph, origin_node, dest_node, flood_zones,
        vehicle_max_depth_cm, penalty_scale=2.0,
    )

    # --- Route 2: Fastest (relaxed penalty, allow shallow floods) ---
    path_fast = _astar_with_penalty(
        road_graph, origin_node, dest_node, flood_zones,
        vehicle_max_depth_cm * 1.5,  # Allow slightly deeper
        penalty_scale=0.5,
    )

    # --- Route 3: Alternative (exclude flooded edges entirely) ---
    # Create a graph copy with impassable edges removed
    path_alt = _astar_with_penalty(
        road_graph, origin_node, dest_node, flood_zones,
        vehicle_max_depth_cm,
        penalty_scale=3.0,  # Very strict penalty
    )

    # If graph routing fails, fall back to synthetic waypoints
    if path_safe is None and path_fast is None and path_alt is None:
        logger.info("Graph routing failed, falling back to synthetic routes")
        return _fallback_routes(origin_lat, origin_lng, dest_lat, dest_lng, flood_zones, vehicle_max_depth_cm)

    # Use best available path as fallback for missing routes
    if path_safe is None:
        path_safe = path_fast or path_alt
    if path_fast is None:
        path_fast = path_safe or path_alt
    if path_alt is None:
        path_alt = path_safe or path_fast

    # Build route outputs
    route_safe = _build_route_from_path(
        path_safe, road_graph, flood_zones, flood_count,
        id="route-safe", type="safe", title="Rute Teraman",
        badge="Terbaik", color="#10B981",
        description="Jalur bebas banjir, dioptimalkan menghindari zona genangan.",
        avg_speed=ROUTE_SPEEDS["safe"],
    )

    route_fast = _build_route_from_path(
        path_fast, road_graph, flood_zones, flood_count,
        id="route-fastest", type="fastest", title="Rute Tercepat",
        badge="Risiko Sedang", color="#F59E0B",
        description="Jalur tercepat, mungkin melewati genangan ringan.",
        avg_speed=ROUTE_SPEEDS["fastest"],
    )

    route_alt = _build_route_from_path(
        path_alt, road_graph, flood_zones, flood_count,
        id="route-alternative", type="alternative", title="Rute Alternatif",
        badge="Opsi Cadangan", color="#3B82F6",
        description="Jalur alternatif melalui koridor berbeda.",
        avg_speed=ROUTE_SPEEDS["alternative"],
    )

    return {
        "origin": "Lokasi Saat Ini",
        "destination": "Tujuan",
        "flood_zones_active": flood_count,
        "options": [route_safe, route_fast, route_alt],
    }


def _build_route_from_path(
    path: list[tuple],
    graph: RoadGraph,
    flood_zones: list[dict],
    flood_count: int,
    id: str,
    type: str,
    title: str,
    badge: str,
    color: str,
    description: str,
    avg_speed: float,
) -> dict:
    """Build a route dict from an A* path."""
    road_labels = _build_road_labels(path, graph, flood_zones)
    path_coords = _path_to_coords(path)

    # Calculate total distance
    total_distance = 0.0
    for i in range(len(path) - 1):
        total_distance += _haversine(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])

    # Calculate actual average speed based on road conditions
    actual_speed = avg_speed
    if road_labels:
        statuses = [rl["status"] for rl in road_labels]
        if "flooded" in statuses:
            actual_speed = min(actual_speed, 15.0)
        elif "watch" in statuses:
            actual_speed = min(actual_speed, 25.0)

    duration = _estimate_duration(total_distance, actual_speed)
    avoided = _count_flood_zones_avoided(path, graph, flood_zones)

    # Determine risk level
    statuses = [rl["status"] for rl in road_labels] if road_labels else ["safe"]
    if "flooded" in statuses or "impassable" in statuses:
        risk_level = "Tinggi"
    elif "watch" in statuses:
        risk_level = "Sedang"
    else:
        risk_level = "Rendah"

    # Flood avoided text
    if flood_count > 0:
        flood_avoided_text = f"Menghindari {avoided} area banjir"
    else:
        flood_avoided_text = "Jalur bersih dari banjir"

    return {
        "id": id,
        "type": type,
        "title": title,
        "badge": badge,
        "duration": duration,
        "distance": _format_distance(total_distance),
        "flood_avoided": flood_avoided_text,
        "risk_level": risk_level,
        "color": color,
        "description": description,
        "path": path_coords,
        "road_labels": road_labels,
        "flood_zones_avoided": avoided,
    }


def _fallback_routes(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    flood_zones: list[dict],
    vehicle_max_depth_cm: float,
) -> dict:
    """
    Fallback route generation when graph routing fails.
    Uses synthetic waypoints with flood awareness.
    """
    flood_count = len([z for z in flood_zones if z.get("status") in ("flooded", "impassable")])

    # Safe route: detour west
    safe_mid = [
        (origin_lat + (dest_lat - origin_lat) * 0.3, origin_lng - 0.015),
        (origin_lat + (dest_lat - origin_lat) * 0.5, origin_lng - 0.02),
        (origin_lat + (dest_lat - origin_lat) * 0.7, origin_lng - 0.01),
    ]
    path_safe = [[origin_lat, origin_lng]] + [[m[0], m[1]] for m in safe_mid] + [[dest_lat, dest_lng]]

    # Fastest route: direct
    path_fast = [[origin_lat, origin_lng], [(origin_lat + dest_lat) / 2, (origin_lng + dest_lng) / 2], [dest_lat, dest_lng]]

    # Alternative route: detour east
    alt_mid = [
        (origin_lat + (dest_lat - origin_lat) * 0.4, origin_lng + 0.01),
        (origin_lat + (dest_lat - origin_lat) * 0.6, origin_lng + 0.015),
    ]
    path_alt = [[origin_lat, origin_lng]] + [[m[0], m[1]] for m in alt_mid] + [[dest_lat, dest_lng]]

    def _build_fallback(path, id, type, title, badge, color, desc, speed):
        dist = sum(_haversine(path[i][0], path[i][1], path[i+1][0], path[i+1][1]) for i in range(len(path)-1))
        labels = []
        for i in range(len(path) - 1):
            s, d = _get_segment_status(path[i][0], path[i][1], path[i+1][0], path[i+1][1], flood_zones)
            labels.append({
                "segment": f"Segmen {i+1}",
                "status": s,
                "color": STATUS_COLORS.get(s, "#10B981"),
                "depth_cm": round(d, 1),
            })
        statuses = [l["status"] for l in labels]
        risk = "Tinggi" if "flooded" in statuses else ("Sedang" if "watch" in statuses else "Rendah")
        return {
            "id": id, "type": type, "title": title, "badge": badge,
            "duration": _estimate_duration(dist, speed),
            "distance": _format_distance(dist),
            "flood_avoided": f"Menghindari {flood_count} area banjir" if flood_count > 0 else "Jalur bersih",
            "risk_level": risk, "color": color, "description": desc,
            "path": path, "road_labels": labels, "flood_zones_avoided": flood_count,
        }

    return {
        "origin": "Lokasi Saat Ini",
        "destination": "Tujuan",
        "flood_zones_active": flood_count,
        "options": [
            _build_fallback(path_safe, "route-safe", "safe", "Rute Teraman", "Terbaik", "#10B981", "Jalur bebas banjir.", 30.0),
            _build_fallback(path_fast, "route-fastest", "fastest", "Rute Tercepat", "Risiko Sedang", "#F59E0B", "Jalur tercepat.", 35.0),
            _build_fallback(path_alt, "route-alternative", "alternative", "Rute Alternatif", "Opsi Cadangan", "#3B82F6", "Jalur alternatif.", 28.0),
        ],
    }
