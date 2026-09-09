"""
Road Graph Builder — Converts OSM road data into a NetworkX graph for A* routing.

Loads data/processed/roads_graph.json and builds a directed graph where:
- Nodes = unique coordinate endpoints (snapped to grid for connectivity)
- Edges = road segments with distance, name, highway type, and full coords

Uses two-level snapping:
1. Coarse snap (0.0005 deg ≈ 55m) for endpoint merging across segments
2. Fine snap (0.0001 deg ≈ 11m) for nearest-node lookups
"""
import json
import math
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
ROADS_FILE = DATA_DIR / "roads_graph.json"

# Coarse snap: for merging endpoints across road segments (~550m tolerance)
COARSE_PRECISION = 2  # 0.005 degrees ≈ 550m

# Fine snap: for nearest-node lookups (~11m tolerance)
FINE_PRECISION = 5  # 0.0001 degrees ≈ 11m

# Highway type priority (higher = more important for routing)
HIGHWAY_PRIORITY = {
    "motorway": 10,
    "trunk": 9,
    "primary": 8,
    "primary_link": 7,
    "secondary": 6,
    "secondary_link": 5,
    "tertiary": 4,
    "tertiary_link": 3,
    "residential": 2,
    "unclassified": 1,
    "service": 1,
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
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


def _snap_key(lat: float, lng: float, precision: int = COARSE_PRECISION) -> tuple:
    """Snap coordinates to grid for node deduplication."""
    return (round(lat, precision), round(lng, precision))


@dataclass
class RoadEdge:
    road_id: int
    name: str
    highway: str
    coords: list  # [[lat, lng], ...]
    distance_km: float
    start_node: tuple
    end_node: tuple


class RoadGraph:
    """
    Road graph for A* routing over Semarang road network.

    Usage:
        graph = RoadGraph.load()
        path = graph.find_nearest_node(-7.05, 110.44)
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.edges_data: dict[tuple, RoadEdge] = {}  # (start, end) -> RoadEdge
        self._loaded = False

    @classmethod
    def load(cls, force_reload: bool = False) -> "RoadGraph":
        """Load and build graph from roads_graph.json. Cached after first load."""
        if not hasattr(cls, "_instance") or force_reload:
            cls._instance = cls()
            cls._instance._build()
        return cls._instance

    def _build(self):
        """Build the graph from JSON data with aggressive connectivity."""
        if not ROADS_FILE.exists():
            logger.error(f"Roads file not found: {ROADS_FILE}")
            return

        with open(ROADS_FILE) as f:
            roads = json.load(f)

        logger.info(f"Building road graph from {len(roads)} segments...")

        # Pass 1: Collect all endpoints and snap to coarse grid
        node_registry: dict[tuple, list[float]] = {}

        for road in roads:
            coords = road["coords"]
            if len(coords) < 2:
                continue

            for coord in [coords[0], coords[-1]]:
                coarse_key = _snap_key(coord[0], coord[1])
                if coarse_key not in node_registry:
                    node_registry[coarse_key] = [coord[0], coord[1]]

        # Create fine-snap index for nearest-node lookups
        self._node_positions: dict[tuple, tuple] = {}
        for coarse_key, pos in node_registry.items():
            fine_key = _snap_key(pos[0], pos[1], FINE_PRECISION)
            self._node_positions[fine_key] = coarse_key

        logger.info(f"Node registry: {len(node_registry)} unique nodes")

        # Pass 2: Build edges from road segments
        edges_added = 0
        for road in roads:
            coords = road["coords"]
            if len(coords) < 2:
                continue

            start_node = _snap_key(coords[0][0], coords[0][1])
            end_node = _snap_key(coords[-1][0], coords[-1][1])

            if start_node == end_node:
                continue

            if start_node not in node_registry:
                node_registry[start_node] = [coords[0][0], coords[0][1]]
            if end_node not in node_registry:
                node_registry[end_node] = [coords[-1][0], coords[-1][1]]

            total_dist = 0.0
            for i in range(len(coords) - 1):
                total_dist += _haversine(
                    coords[i][0], coords[i][1],
                    coords[i + 1][0], coords[i + 1][1],
                )

            edge = RoadEdge(
                road_id=road["id"],
                name=road.get("name", "Unnamed"),
                highway=road.get("highway", "residential"),
                coords=coords,
                distance_km=total_dist,
                start_node=start_node,
                end_node=end_node,
            )

            start_pos = node_registry[start_node]
            end_pos = node_registry[end_node]
            self.graph.add_node(start_node, lat=start_pos[0], lng=start_pos[1])
            self.graph.add_node(end_node, lat=end_pos[0], lng=end_pos[1])

            self.edges_data[(start_node, end_node)] = edge
            self.edges_data[(end_node, start_node)] = RoadEdge(
                road_id=road["id"],
                name=road.get("name", "Unnamed"),
                highway=road.get("highway", "residential"),
                coords=list(reversed(coords)),
                distance_km=total_dist,
                start_node=end_node,
                end_node=start_node,
            )

            priority = HIGHWAY_PRIORITY.get(road.get("highway", ""), 1)
            self.graph.add_edge(
                start_node, end_node,
                weight=total_dist,
                road_id=road["id"],
                name=road.get("name", "Unnamed"),
                highway=road.get("highway", "residential"),
                priority=priority,
            )
            self.graph.add_edge(
                end_node, start_node,
                weight=total_dist,
                road_id=road["id"],
                name=road.get("name", "Unnamed"),
                highway=road.get("highway", "residential"),
                priority=priority,
            )
            edges_added += 1

        self._node_registry = node_registry
        self._loaded = True

        num_components = nx.number_weakly_connected_components(self.graph)
        largest_cc = max(nx.weakly_connected_components(self.graph), key=len)
        logger.info(
            f"Road graph built: {self.graph.number_of_nodes()} nodes, "
            f"{edges_added} road edges, "
            f"{num_components} components, largest: {len(largest_cc)} nodes"
        )

    def find_nearest_node(self, lat: float, lng: float) -> Optional[tuple]:
        """Find the nearest graph node to a GPS coordinate."""
        if not self._loaded:
            return None

        # Try fine-snap index first
        fine_key = _snap_key(lat, lng, FINE_PRECISION)
        if fine_key in self._node_positions:
            return self._node_positions[fine_key]

        # Try coarse-snap directly
        coarse_key = _snap_key(lat, lng)
        if coarse_key in self.graph:
            return coarse_key

        # Brute-force search nearest node (acceptable for ~9K nodes)
        best_dist = float("inf")
        best_node = None
        for node in self.graph.nodes():
            d = _haversine(lat, lng, node[0], node[1])
            if d < best_dist:
                best_dist = d
                best_node = node

        return best_node

    def get_edge_data(self, u: tuple, v: tuple) -> Optional[RoadEdge]:
        """Get the RoadEdge between two nodes."""
        return self.edges_data.get((u, v))

    def get_edge_distance(self, u: tuple, v: tuple) -> float:
        """Get haversine distance between two nodes in km."""
        return _haversine(u[0], u[1], v[0], v[1])

    def nodes_in_range(self, lat: float, lng: float, radius_km: float) -> list:
        """Find all nodes within radius_km of a point."""
        results = []
        for node in self.graph.nodes():
            d = _haversine(lat, lng, node[0], node[1])
            if d <= radius_km:
                results.append((node, d))
        return sorted(results, key=lambda x: x[1])

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()
