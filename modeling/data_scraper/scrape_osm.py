"""
Scrape OSM data for Semarang — Fixed version
"""
import httpx
import json
import time
import urllib.parse

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = "-7.10,110.30,-6.90,110.55"
OUTDIR = r"C:\Users\Joshevan\Downloads\Deteksi-Banjir\modeling\data\raw"

QUERIES = {
    "roads": f'[out:json][timeout:90];(way["highway"~"primary|secondary|tertiary|residential"]({BBOX}););out body;>;out skel;',
    "waterways": f'[out:json][timeout:90];(way["waterway"~"river|stream|drain|canal"]({BBOX}););out body;>;out skel;',
    "drainage": f'[out:json][timeout:90];(way["waterway"~"drain"]({BBOX});way["man_made"~"storm_drain"]({BBOX}););out body;>;out skel;',
    "land_use": f'[out:json][timeout:90];(way["landuse"]({BBOX}););out body;>;out skel;',
}

HEADERS = {
    "User-Agent": "SafeRoute/1.0 (flood-detection-project)",
    "Accept": "application/json",
}

def main():
    results = {}
    with httpx.Client(timeout=120.0, headers=HEADERS) as client:
        for name, query in QUERIES.items():
            print(f"Fetching {name}...")
            try:
                # Try GET with data parameter
                resp = client.get(f"{OVERPASS_URL}?data={urllib.parse.quote(query)}")
                resp.raise_for_status()
                data = resp.json()
                elements = data.get("elements", [])
                print(f"  {name}: {len(elements)} elements")
                results[name] = data
            except Exception as e:
                print(f"  GET failed for {name}: {e}")
                try:
                    # Fallback: POST with form data
                    resp = client.post(OVERPASS_URL, content=query.encode("utf-8"), headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"})
                    resp.raise_for_status()
                    data = resp.json()
                    elements = data.get("elements", [])
                    print(f"  {name} (POST): {len(elements)} elements")
                    results[name] = data
                except Exception as e2:
                    print(f"  POST also failed for {name}: {e2}")
            time.sleep(3)

    for name, data in results.items():
        path = f"{OUTDIR}/osm_{name}.json"
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"Saved {path}")

    print(f"\nTotal: {len(results)} OSM datasets scraped")

if __name__ == "__main__":
    main()
