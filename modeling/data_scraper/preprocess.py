"""
Preprocess all scraped data into processed format.
"""
import json
import csv
from pathlib import Path

RAW_DIR = Path(r"C:\Users\Joshevan\Downloads\Deteksi-Banjir\modeling\data\raw")
PROC_DIR = Path(r"C:\Users\Joshevan\Downloads\Deteksi-Banjir\modeling\data\processed")
PROC_DIR.mkdir(parents=True, exist_ok=True)


def preprocess_roads():
    print("=== Preprocessing OSM Roads ===")
    with open(RAW_DIR / "osm_roads.json") as f:
        roads = json.load(f)

    nodes = {e["id"]: (e.get("lat", 0), e.get("lon", 0)) for e in roads["elements"] if e["type"] == "node"}
    ways = [e for e in roads["elements"] if e["type"] == "way"]

    road_graph = []
    for way in ways[:5000]:
        tags = way.get("tags", {})
        node_refs = way.get("nodes", [])
        coords = []
        for nid in node_refs:
            if nid in nodes:
                coords.append(list(nodes[nid]))
        if len(coords) >= 2:
            road_graph.append({
                "id": way["id"],
                "name": tags.get("name", ""),
                "highway": tags.get("highway", ""),
                "coords": coords,
            })

    with open(PROC_DIR / "roads_graph.json", "w") as f:
        json.dump(road_graph, f)
    print(f"  Roads graph: {len(road_graph)} segments")
    return road_graph


def preprocess_waterways():
    print("=== Preprocessing OSM Waterways ===")
    with open(RAW_DIR / "osm_waterways.json") as f:
        waterways = json.load(f)

    ww_nodes = {e["id"]: (e.get("lat", 0), e.get("lon", 0)) for e in waterways["elements"] if e["type"] == "node"}
    ww_ways = [e for e in waterways["elements"] if e["type"] == "way"]

    waterway_graph = []
    for way in ww_ways:
        tags = way.get("tags", {})
        coords = [list(ww_nodes[nid]) for nid in way.get("nodes", []) if nid in ww_nodes]
        if len(coords) >= 2:
            waterway_graph.append({
                "id": way["id"],
                "name": tags.get("name", ""),
                "waterway": tags.get("waterway", ""),
                "coords": coords,
            })

    with open(PROC_DIR / "waterways_graph.json", "w") as f:
        json.dump(waterway_graph, f)
    print(f"  Waterways: {len(waterway_graph)} segments")
    return waterway_graph


def preprocess_drainage():
    print("=== Preprocessing OSM Drainage ===")
    with open(RAW_DIR / "osm_drainage.json") as f:
        drainage = json.load(f)

    dr_nodes = {e["id"]: (e.get("lat", 0), e.get("lon", 0)) for e in drainage["elements"] if e["type"] == "node"}
    dr_ways = [e for e in drainage["elements"] if e["type"] == "way"]

    drainage_graph = []
    for way in dr_ways:
        tags = way.get("tags", {})
        coords = [list(dr_nodes[nid]) for nid in way.get("nodes", []) if nid in dr_nodes]
        if len(coords) >= 2:
            drainage_graph.append({
                "id": way["id"],
                "name": tags.get("name", ""),
                "type": tags.get("waterway", tags.get("man_made", "")),
                "coords": coords,
            })

    with open(PROC_DIR / "drainage_graph.json", "w") as f:
        json.dump(drainage_graph, f)
    print(f"  Drainage: {len(drainage_graph)} segments")
    return drainage_graph


def preprocess_kaggle():
    print("=== Preprocessing Kaggle Flood Dataset ===")
    kaggle_dir = RAW_DIR / "flood_kaggle"
    csv_files = list(kaggle_dir.glob("*.csv"))
    print(f"  CSV files found: {[f.name for f in csv_files]}")

    for csv_file in csv_files:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        summary = {
            "source": "Kaggle - Flood Prediction Dataset",
            "file": csv_file.name,
            "total_rows": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "sample_rows": rows[:5],
        }
        out_name = csv_file.stem + "_summary.json"
        with open(PROC_DIR / out_name, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"  {csv_file.name}: {len(rows)} rows, {len(summary['columns'])} columns")


def preprocess_weather():
    print("=== Preprocessing BMKG Weather ===")
    with open(RAW_DIR / "bmkg_weather.json") as f:
        weather = json.load(f)

    with open(PROC_DIR / "weather_current.json", "w") as f:
        json.dump(weather, f, indent=2)
    print(f"  Weather data saved")


def main():
    preprocess_roads()
    preprocess_waterways()
    preprocess_drainage()
    preprocess_kaggle()
    preprocess_weather()

    print("\n=== Preprocessing Complete ===")
    print("Files in processed/:")
    for f in sorted(PROC_DIR.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes")


if __name__ == "__main__":
    main()
