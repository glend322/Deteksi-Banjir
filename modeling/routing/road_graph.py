"""
Road Graph Builder — Converts OSM road data into a NetworkX graph for A* routing.

Loads data/processed/roads_graph.json and builds a directed graph where:
- Nodes = unique coordinate endpoints (snapped to grid for connectivity)
- Edges = road segments with distance, name, highway type, and full coords
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

# Snap grid: coordinates rounded to this precision for node merging
# ~5 decimal places ≈ 1.1m precision
SNAP_PRECISION = 5

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


def _snap_key(lat: float, lng: float) -> tuple:
    """Snap coordinates to grid for node deduplication."""
    return (round(lat, SNAP_PRECISION), round(lng, SNAP_PRECISION))


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
        """Build the graph from JSON data."""
        if not ROADS_FILE.exists():
            logger.error(f"Roads file not found: {ROADS_FILE}")
            return

        with open(ROADS_FILE) as f:
            roads = json.load(f)

        logger.info(f"Building road graph from {len(roads)} segments...")

        for road in roads:
            coords = road["coords"]
            if len(coords) < 2:
                continue

            start_node = _snap_key(coords[0][0], coords[0][1])
            end_node = _snap_key(coords[-1][0], coords[-1][1])

            if start_node == end_node:
                continue

            # Calculate total distance along the segment
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

            # Add nodes
            self.graph.add_node(start_node, lat=coords[0][0], lng=coords[0][1])
            self.graph.add_node(end_node, lat=coords[-1][0], lng=coords[-1][1])

            # Add edge (both directions for undirected routing)
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
                reverse_weight=total_dist,
                road_id=road["id"],
                name=road.get("name", "Unnamed"),
                highway=road.get("highway", "residential"),
                priority=priority,
            )
            self.graph.add_edge(
                end_node, start_node,
                weight=total_dist,
                reverse_weight=total_dist,
                road_id=road["id"],
                name=road.get("name", "Unnamed"),
                highway=road.get("highway", "residential"),
                priority=priority,
            )

        self._loaded = True
        logger.info(
            f"Road graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )

    def find_nearest_node(self, lat: float, lng: float) -> Optional[tuple]:
        """Find the nearest graph node to a GPS coordinate."""
        if not self._loaded:
            return None

        target = _snap_key(lat, lng)
        if target in self.graph:
            return target

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
