# SafeRoute Modeling

AI/ML backbone untuk SafeRoute — Flood Detection & Safe Route Recommendation.

## 2 Core Capabilities

1. **Safe Route Engine** — Kalkulasi rute aman dengan flood penalty + evakuasi terdekat
2. **CCTV Flood Detection Pipeline** — CCTV → CV → Verify → Classify (dangkal/sedang/dalam) → Notifikasi

## Quick Start

```bash
cd modeling
pip install -r requirements.txt
cp .env.example .env
```

### Run Single CCTV Scan

```bash
python detector.py --once
```

### Run Continuous Monitoring

```bash
python worker.py --interval 60
```

### Start API Server

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Output Format

```
Daerah Kaligawe banjir di tingkat dalam
Daerah Genuk banjir di tingkat sedang
Daerah Mangkang banjir di tingkat dangkal
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
├── MODELING_PRD.md          # Product requirements
├── README.md                # This file
├── requirements.txt
├── .env.example
├── .gitignore
├── cctv_client.py           # Stage 1: CCTV scraping + HLS frame extraction
├── cv_model.py              # Stage 2: CNN flood detection architecture
├── verifier.py              # Stage 3: False positive filter
├── classifier.py            # Stage 4: dangkal/sedang/dalam classification
├── detector.py              # Stage 5: Pipeline orchestrator
├── area_mapping.py          # Reverse geocode → nama daerah
├── route_engine.py          # A* routing with flood penalty
├── evacuation_finder.py     # Nearest evacuation point
├── worker.py                # Background monitoring worker
├── api/
│   ├── main.py
│   ├── schemas.py
│   └── dependencies.py
├── data_scraper/
│   ├── utils.py
│   ├── bmkg_scraper.py
│   ├── osm_scraper.py
│   ├── kaggle_downloader.py
│   └── config.yaml
├── checkpoints/             # Model weights
└── data/
    ├── README.md
    ├── raw/
    ├── processed/
    └── sample/
```
