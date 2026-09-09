# SafeRoute Modeling

AI/ML backbone untuk SafeRoute — Flood Detection & Safe Route Recommendation.

## 3 Core Modules

1. **`detection/`** — CV Flood Detection Pipeline (CCTV → CV → Verify → Classify)
2. **`routing/`** — Safe Route Engine (A* routing + evakuasi terdekat)
3. **`api/`** — FastAPI Endpoints

## Quick Start

```bash
cd modeling
pip install -r requirements.txt
cp .env.example .env
```

### Run Single CCTV Scan

```bash
python -m detection.detector --once
```

### Run Continuous Monitoring

```bash
python -m detection.worker --interval 60
```

### Start API Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### Run Tests

```bash
python test_classification.py    # CV model tests
python test_pipeline.py          # Pipeline integration tests
python test_routing_graph.py     # A* routing tests
python test_api.py               # API endpoint tests
python test_model_inference.py   # Model accuracy benchmark
```

## Output Format

```
Daerah Semarang Utara banjir tingkat sedang. Penyebab genangan air hujan.
```

## Classification

| Depth | Kategori | Warna | Status |
|---|---|---|---|
| < 20cm | dangkal | #F59E0B | watch |
| 20-40cm | sedang | #F97316 | flooded |
| > 40cm | dalam | #EF4444 | impassable |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/classify-image` | POST | Classify a single image |
| `/api/scan-cctv` | POST | Scan all CCTV cameras |
| `/api/calculate-route` | POST | Calculate safe routes |
| `/api/flood-zones` | GET | Get active flood zones |
| `/api/evacuation-points` | GET | Get evacuation points |
| `/health` | GET | Health check |

---

## System Workflow — Feature 1: CCTV Flood Detection Pipeline

An end-to-end pipeline that automatically detects flooding from CCTV cameras in Semarang, classifies severity, and generates notifications.

### Pipeline Flow (5 Stages)

```
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 1: CCTV CLIENT                         │
│                    (cctv_client.py)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: Category UUIDs for flood-related CCTV                   │
│  Source: pantausemar.semarangkota.go.id                         │
│                                                                 │
│  Step 1: Scrape HTML page per category                          │
│    → Extract JSON from `var cctvs = [...]` in page source       │
│    → Parse camera ID, name, lat/lng, stream URLs                │
│                                                                 │
│  Step 2: Filter for HLS streams (.m3u8 URLs only)               │
│    → Skip non-video links                                       │
│    → Deduplicate by (cctv_id, link_id)                          │
│                                                                 │
│  Step 3: Extract frame from HLS stream                          │
│    → Primary: ffmpeg subprocess (1 frame from .m3u8)            │
│    → Fallback: HTTP download .ts segment → ffmpeg → JPEG        │
│                                                                 │
│  Output: CCTVFrame(camera_id, name, lat, lng, frame_bytes)      │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ JPEG frame bytes
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 2: CV DETECTION                        │
│                    (cv_model.py)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Model: FloodClassifier (Multi-head CNN)                        │
│  Backbone: MobileNetV3-Small (from checkpoint)                  │
│  Input: 224x224 RGB image tensor                                │
│                                                                 │
│  Architecture:                                                  │
│    Backbone → 576-d feature vector                              │
│    ├── Classification Head → [no_flood, flood] (softmax)        │
│    ├── Depth Classification Head → [dangkal, sedang, dalam]     │
│    ├── Depth Regression Head → continuous depth value (cm)       │
│    └── Cause Detection Head → [river, trash] (sigmoid)          │
│                                                                 │
│  Output:                                                        │
│    flood_detected: bool                                          │
│    confidence: float (0-1)                                       │
│    depth_label: "dangkal"|"sedang"|"dalam"                       │
│    river_detected: bool                                          │
│    trash_detected: bool                                          │
│    cause_text: "sungai meluap" / "sampah menyumbat" / etc       │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ CV result dict
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 3: VERIFIER                            │
│                    (verifier.py)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Purpose: Filter false positives from CV model                  │
│                                                                 │
│  Rule-based checks:                                             │
│    1. Confidence gate: < 0.95 → reject                          │
│    2. Depth gate: < 5cm → reject (too small)                    │
│    3. Brightness: too dark (<30) or too bright (>240) → flag    │
│    4. Water area ratio: < 20% of frame → flag                   │
│    5. Water texture: high variance → flag (not smooth water)    │
│    6. Water reflection: high edge ratio → flag (not water)      │
│    7. Temporal consistency: 3+ recent detections → boost conf   │
│                                                                 │
│  Confidence modifier: -0.5 to +0.3 based on checks              │
│                                                                 │
│  Output: is_genuine_flood (bool), confidence_modifier            │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ verified result
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 4: CLASSIFIER                           │
│                    (classifier.py)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Maps depth + cause to classification + notification text        │
│                                                                 │
│  Depth → Status:                                                 │
│    dangkal (<20cm)  → "watch"    → #F59E0B (kuning)             │
│    sedang (20-40cm) → "flooded"  → #F97316 (orange)             │
│    dalam (>40cm)    → "impassable" → #EF4444 (merah)            │
│                                                                 │
│  Cause → Text:                                                   │
│    river detected   → "sungai meluap"                            │
│    trash detected   → "sampah menyumbat saluran"                 │
│    both detected    → "sungai meluap dan sampah menyumbat"       │
│    neither detected → "genangan air hujan"                       │
│                                                                 │
│  Output: "Daerah {area} banjir tingkat {classification}.         │
│           Penyebab {cause}."                                     │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ FloodDetection dataclass
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 5: ORCHESTRATOR                         │
│                    (detector.py)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FloodDetectionPipeline:                                        │
│    1. Initialize all components (lazy loading)                   │
│    2. Scrape all CCTV cameras (with semaphore limit=5)          │
│    3. For each camera:                                           │
│       a. Extract frame from HLS                                 │
│       b. Run CV inference                                        │
│       c. Run false positive filter                               │
│       d. Check baseline water level (BaselineTracker)            │
│       e. Get area name (area_mapping.py)                         │
│       f. Classify severity                                       │
│       g. Build FloodDetection result                             │
│    4. Save baseline updates                                      │
│    5. Return list of FloodDetection                              │
│                                                                 │
│  BaselineTracker: Tracks normal water level per camera           │
│    - Compares current water ratio vs historical mean             │
│    - Uses exponential moving average (alpha=0.1)                 │
│    - Detects real flood vs normal water body                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Background Worker (worker.py)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLOOD DETECTION WORKER                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Runs in infinite loop:                                         │
│    while True:                                                   │
│      1. scan_cycle() → pipeline.run_scan()                      │
│      2. For each flood detection:                                │
│         - Check cooldown (15 min per camera)                     │
│         - If cooldown expired → send alert to backend            │
│         - POST /api/internal/ai/predictions                      │
│      3. Sleep(interval) → default 60 seconds                     │
│                                                                 │
│  Alert payload:                                                  │
│    source_name, location_name, area, lat, lng,                   │
│    estimated_depth_cm, classification, confidence,               │
│    alert_needed, cause                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Workflow — Feature 2: Safe Route Engine

Calculates 3 safe route options from origin to destination, considering real-time flood conditions using A* algorithm with flood penalties.

### Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  {                                                              │
│    "origin": {"lat": -7.0505, "lng": 110.4410},                │
│    "destination": {"lat": -6.9644, "lng": 110.4281},           │
│    "vehicle_max_depth_cm": 30,                                  │
│    "flood_zones": [                                             │
│      {"lat": -6.99, "lng": 110.42, "status": "flooded",        │
│       "depth_cm": 50, "radius_km": 1.5}                        │
│    ]                                                            │
│  }                                                              │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: LOAD ROAD GRAPH                       │
│                    (road_graph.py)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Source: data/processed/roads_graph.json                         │
│  (5,000 OSM road segments from Semarang)                        │
│                                                                 │
│  Build NetworkX DiGraph:                                         │
│    - Nodes: unique coordinate endpoints (coarse-snapped)         │
│    - Edges: road segments with attributes:                       │
│      * road_id, name, highway_type, distance_km, coords         │
│                                                                 │
│  Coarse snapping: 0.005 degrees ≈ 550m tolerance                │
│  (connects nearby endpoints from different segments)             │
│                                                                 │
│  Result: ~8,700 nodes, ~9,900 edges                             │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: SNAP TO GRAPH                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  origin_lat/lng → find_nearest_node() → origin_node             │
│  dest_lat/lng → find_nearest_node() → dest_node                 │
│                                                                 │
│  Uses fine-snap index (0.0001 deg ≈ 11m) for fast lookup        │
│  Falls back to brute-force haversine search                      │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: A* PATHFINDING                        │
│                    (route_engine.py)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Algorithm: networkx.astar_path() with custom cost function     │
│                                                                 │
│  cost(u, v) = base_distance(u, v) x flood_penalty(status)      │
│                                                                 │
│  Flood Penalty Table:                                            │
│    safe     = 1.0  (no penalty)                                  │
│    watch    = 1.5  (shallow, <20cm)                              │
│    flooded  = 3.0  (moderate, 20-40cm)                           │
│    impassable = INF  (deep >40cm, excluded)                      │
│                                                                 │
│  Vehicle filter:                                                 │
│    If segment depth > vehicle_max_depth_cm → penalty = INF       │
│                                                                 │
│  Heuristic: haversine distance to destination                    │
│                                                                 │
│  Runs 3 times with different penalty scales:                     │
│    Safe:        penalty_scale=2.0 (strict avoidance)             │
│    Fastest:     penalty_scale=0.5 (allow shallow floods)         │
│    Alternative: penalty_scale=3.0 (very strict, different path)  │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ List of (lat,lng) waypoints
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 4: ROAD LABELING                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each edge in the path:                                      │
│    1. Get road name from graph data                              │
│    2. Check flood status along edge coords                       │
│    3. Assign color:                                              │
│       safe     → #10B981 (green)                                 │
│       watch    → #F59E0B (yellow)                                │
│       flooded  → #F97316 (orange)                                │
│       impassable → #EF4444 (red)                                 │
│    4. Output: {segment: "Jalan X", status, color, depth_cm}      │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 5: BUILD OUTPUT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each route option:                                          │
│    - Calculate total distance (sum haversine)                    │
│    - Estimate duration (distance / avg_speed)                    │
│    - Count flood zones avoided                                   │
│    - Determine risk level                                        │
│    - Format as RouteOption dict                                  │
│                                                                 │
│  Also find nearest evacuation point:                             │
│    - Haversine distance to all 5 evacuation points               │
│    - Filter by active status                                     │
│    - Return closest one                                          │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  {                                                              │
│    "origin": "Lokasi Saat Ini",                                 │
│    "destination": "Tujuan",                                     │
│    "flood_zones_active": 1,                                     │
│    "options": [                                                 │
│      {                                                          │
│        "id": "route-safe",                                      │
│        "title": "Rute Teraman",                                 │
│        "distance": "14,9 km",                                   │
│        "duration": "29 menit",                                  │
│        "risk_level": "Rendah",                                  │
│        "color": "#10B981",                                      │
│        "path": [[-7.05, 110.44], ...],                          │
│        "road_labels": [                                         │
│          {"segment": "Jalan Profesor Soedarto",                 │
│           "status": "safe", "color": "#10B981", "depth_cm": 0}  │
│        ]                                                        │
│      },                                                         │
│      ... (fastest, alternative)                                 │
│    ],                                                           │
│    "nearest_evacuation": {...}                                   │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Workflow — Feature 3: Area Mapping

Reverse geocodes GPS coordinates to Semarang administrative area names (kecamatan/kelurahan).

```
Input: lat=-6.9535, lng=110.4570
         ↓
Load static database of 33 known flood-prone areas
         ↓
For each area: calculate haversine distance to input
         ↓
Find closest match:
  < 1.0 km → "Kelurahan, Kecamatan" (e.g., "Trimulyo, Genuk")
  < 3.0 km → "Kecamatan" (e.g., "Genuk")
  > 3.0 km → "Semarang" (fallback)
         ↓
Output: "Trimulyo, Genuk"
```

---

## System Workflow — Feature 4: Evacuation Finder

Finds the nearest active evacuation point from user's location.

```
Input: user_lat, user_lng
         ↓
Load 5 hardcoded evacuation points:
  1. Posko Utama MAJT
  2. Kantor Camat Genuk
  3. RS Islam Sultan Agung
  4. Posko BPBD Kota Semarang
  5. Kantor SAR Semarang
         ↓
Filter: only "Siap Siaga" or "Aktif Penuh" status
         ↓
Calculate haversine distance to each
         ↓
Return closest with:
  name, lat, lng, distance_km, duration_walk (distance x 12 min/km)
```

---

## System Workflow — Feature 5: FastAPI Endpoints

### Endpoints Overview

| Endpoint | Method | Purpose | Flow |
|---|---|---|---|
| `/api/classify-image` | POST | Classify single image | Image → CV model → result |
| `/api/scan-cctv` | POST | Scan all CCTV cameras | CCTV → CV → Verify → Classify |
| `/api/calculate-route` | POST | Calculate safe routes | GPS → Graph → A* → 3 routes |
| `/api/flood-zones` | GET | Get active flood zones | Return flood zone list |
| `/api/evacuation-points` | GET | Get evacuation points | Return 5 hardcoded points |
| `/health` | GET | Health check | Return status |

### Route Calculation API Flow

```
POST /api/calculate-route
  ↓
Parse request (origin, destination, flood_zones, vehicle_max_depth)
  ↓
Convert flood_zones to dict format
  ↓
Call calculate_safe_routes()
  ↓
Build RoadLabel objects from road_labels
  ↓
Find nearest evacuation point
  ↓
Return RouteCalculateResponse
```

---

## Data Flow Summary

```
CCTV Cameras (Pantau Semarang)
    ↓ HLS stream
cctv_client.py → JPEG frame
    ↓
cv_model.py → flood_detected + depth + cause
    ↓
verifier.py → false positive filter
    ↓
classifier.py → "Daerah X banjir tingkat Y. Penyebab Z."
    ↓
detector.py → FloodDetection result
    ↓
worker.py → POST to backend → notification to frontend

User GPS (lat/lng)
    ↓
area_mapping.py → "Trimulyo, Genuk"
    ↓
route_engine.py → A* with flood penalty
    ↓
3 route options + road_labels + nearest evacuation
    ↓
API response → frontend map rendering
```

---

## Model Performance

| Metric | Result | Target | Status |
|---|---|---|---|
| Flood detection accuracy | 96.7% | > 85% | PASS |
| Flood detection F1 | 0.9655 | — | — |
| Cause detection accuracy | 100% | > 75% | PASS |
| Inference speed (CPU) | 14.2 ms | < 500 ms | PASS |
| Throughput | 70.2 img/s | — | — |

## File Structure

```
modeling/
├── MODELING_PRD.md              # Product requirements
├── README.md                    # This file
├── requirements.txt
├── .env.example
├── .gitignore
│
├── detection/                   # CV Flood Detection
│   ├── __init__.py
│   ├── cctv_client.py           # CCTV scraping + HLS frame extraction
│   ├── cv_model.py              # CNN flood detection architecture
│   ├── verifier.py              # False positive filter
│   ├── classifier.py            # dangkal/sedang/dalam classification
│   ├── detector.py              # Pipeline orchestrator
│   ├── train.py                 # Model training script
│   ├── worker.py                # Background monitoring worker
│   ├── generate_checkpoint.py   # Checkpoint generator
│   └── prepare_training_data.py # Data preparation
│
├── routing/                     # Safe Route Engine
│   ├── __init__.py
│   ├── road_graph.py            # OSM road graph builder (NetworkX)
│   ├── area_mapping.py          # Reverse geocode → nama daerah
│   ├── route_engine.py          # A* routing with flood penalty
│   └── evacuation_finder.py     # Nearest evacuation point
│
├── api/                         # FastAPI Endpoints
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   └── dependencies.py
│
├── data/
│   ├── README.md
│   ├── camera_baselines.json    # Baseline water levels per camera
│   ├── raw/                     # OSM, Kaggle, BMKG data
│   ├── processed/               # Roads, waterways, drainage graphs
│   └── training/                # Flood + nonflood images
│
├── checkpoints/                 # Model weights
├── cache/                       # CCTV cache
├── data_scraper/                # Data preparation tools
├── notebooks/                   # Exploration notebooks
└── test_*.py                    # Test suites
```
