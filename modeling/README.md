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

## Output Format

```
Daerah Semarang Utara banjir tingkat sedang. Penyebab genangan air hujan.
```

## Classification

| Depth | Kategori | Warna |
|---|---|---|
| < 20cm | dangkal | #F59E0B |
| 20-40cm | sedang | #F97316 |
| > 40cm | dalam | #EF4444 |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/classify-image` | POST | Classify a single image |
| `/api/scan-cctv` | POST | Scan all CCTV cameras |
| `/api/calculate-route` | POST | Calculate safe routes |
| `/api/flood-zones` | GET | Get active flood zones |
| `/api/evacuation-points` | GET | Get evacuation points |
| `/health` | GET | Health check |

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
└── notebooks/                   # Exploration notebooks
```
