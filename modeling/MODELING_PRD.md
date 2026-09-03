# Modeling Team — Rules & Specific PRD

**Project:** SafeRoute — AI-Based Flood Detection & Safe Route Recommendation
**Focus:** Kota Semarang
**Date:** 3 September 2026

---

## PART 1: MODELING RULES (Hard Constraints)

### Rule 1 — Folder Isolation
All modeling code, models, datasets, notebooks, configs, tests, and documentation go **exclusively** inside the `modeling/` directory. You are **forbidden** from editing, modifying, or touching any of the following:

- `main.html`
- `css/`
- `js/` (including `data.js` and `app.js`)
- `assets/`
- `PRD_Deteksi_Banjir_Semarang.md`
- `.git/` configuration
- Any root-level files

**Exception:** You may read `js/data.js` to understand the output format the frontend expects, but never modify it.

### Rule 2 — Output Contract
All models must output predictions in a format compatible with the frontend's existing data structure (`SAFEROUTE_DATA` in `js/data.js`). Specifically:
- Flood locations must include `lat`, `lng`, `depth`, `status`, `confidence`
- GeoJSON-compatible where possible for map rendering
- API responses must match the schemas defined in `modeling/api/schemas.py`

### Rule 3 — No Secrets in Code
API keys (BMKG, Mapbox, etc.) must be loaded from environment variables or a `.env` file. Never commit secrets. Add `.env` to `.gitignore` inside `modeling/`.

### Rule 4 — Reproducibility
Every model must have:
- A `requirements.txt` (or reference the root one)
- A README with run instructions
- Saved checkpoints and training configs
- Pinned random seeds for reproducible results

### Rule 5 — Data Provenance
All datasets must be documented in `modeling/data/README.md` with:
- Source URL or origin
- License
- Size (rows, columns, file size)
- Date range covered
- Any preprocessing applied

### Rule 6 — Web Scraping Ethics
When scraping data from external websites:
- Respect `robots.txt`
- Rate-limit requests (max 1 request/second per domain)
- Cache scraped data to avoid re-fetching
- Never scrape private/personally identifiable data
- Document all scraped sources in `data/README.md`

---

## PART 2: SPECIFIC PRD — MODELING SCOPE

### Mission
Build the AI/ML backbone of SafeRoute — 3 core capabilities + a data scraping pipeline, all delivered as Python modules inside `modeling/`.

---

### Capability 1: CV Flood Image Classifier

**Purpose:** Automatically detect flooding from CCTV footage or crowd-sourced photos and estimate water depth.

**Input:**
- Image (JPEG/PNG) or video frame
- Optional: GPS coordinates of the image source

**Output:**
```json
{
  "flood_detected": true,
  "severity": "tergenang",
  "depth_range": "40-70cm",
  "depth_estimate_cm": 55,
  "confidence": 0.87,
  "bounding_boxes": []
}
```

**Severity Classes:**
| Class | Label | Meaning |
|---|---|---|
| 0 | normal | No flooding detected |
| 1 | waspada | Minor water accumulation, watch area |
| 2 | tergenang | Significant flooding, partially impassable |
| 3 | tidak_dapat_dilalui | Severe flooding, road impassable |

**Depth Categories (per PRD 5.1):**
| Range | Status | Vehicle Guidance |
|---|---|---|
| < 20 cm | Normal / Waspada | Safe for motor & mobil |
| 20-40 cm | Tergenang | Motor risk of stalling, mobil relatively safe |
| 40-70 cm | Tidak Dapat Dilalui | Only tall/large vehicles |
| > 70 cm | Tidak Dapat Dilalui | No vehicles recommended |

**Model Architecture:**
- Base: Pre-trained CNN (ResNet50, EfficientNet-B0, or MobileNetV3 for speed)
- Fine-tune on flood image datasets
- Classification head: 4 severity classes
- Regression head: depth estimation (continuous, then bucketed)

**Training Data Sources:**
- Kaggle flood detection datasets
- Scraped CCTV snapshots (see `modeling/scraping/`)
- Augmented with water-color overlays on non-flood street images

**Deliverables:**
```
modeling/cv_classifier/
├── model.py              # Model architecture definition
├── dataset.py            # Dataset & dataloader
├── train.py              # Training loop
├── infer.py              # Single-image inference script
├── evaluate.py           # Metrics (accuracy, F1, MAE for depth)
├── config.yaml           # Hyperparameters
├── checkpoints/          # Saved model weights
└── README.md             # Usage & model card
```

---

### Capability 2: Predictive Flood Risk Model

**Purpose:** Predict which areas will flood in the next 1-6 hours before it happens, using weather data + historical patterns + environmental features.

**Input:**
- Current & recent rainfall (BMKG API, hourly)
- Historical flood records per location
- Elevation / topography (DEM data)
- Drainage quality score
- Land cover / vegetation index
- River water level (if available)
- Time features (hour of day, season, tide schedule for rob-prone areas)

**Output:**
```json
{
  "area_id": "kaligawe",
  "lat": -6.9420,
  "lng": 110.4200,
  "flood_probability": 0.82,
  "predicted_depth_range": "20-40cm",
  "time_window": "next 3 hours",
  "confidence": 0.78,
  "risk_level": "tinggi"
}
```

**Risk Levels:**
| Probability | Risk Level | Action |
|---|---|---|
| < 0.2 | Normal | No alert |
| 0.2-0.5 | Waspada | Advisory notice |
| 0.5-0.8 | Tergenang | Warning + route rerouting |
| > 0.8 | Tidak Dapat Dilalui | Alert + evacuation recommendation |

**Model Options (choose based on data availability):**
- **Option A:** XGBoost/LightGBM (tabular features, fast training, interpretable)
- **Option B:** LSTM/GRU (if time-series rainfall data is rich enough)
- **Option C:** Ensemble of both

**Training Data:**
- Historical flood incident records (location, timestamp, depth, duration)
- BMKG historical hourly rainfall for Semarang
- SRTM DEM elevation data (30m resolution)
- OpenStreetMap data: drainage networks, land use, road density

**Deliverables:**
```
modeling/predictive_model/
├── features.py           # Feature engineering pipeline
├── dataset.py            # PyTorch/Dataset or sklearn pipeline
├── train.py              # Training & cross-validation
├── infer.py              # Prediction for a given area + time
├── evaluate.py           # Metrics (AUC-ROC, precision, recall, MAE)
├── config.yaml           # Hyperparameters
├── checkpoints/          # Saved model
└── README.md
```

---

### Capability 3: Report Verification Engine

**Purpose:** Validate crowd-sourced flood reports from citizens before they appear on the map, reducing false positives.

**Input:**
- Report: location (lat/lng), timestamp, text description, optional photo
- Context: current rainfall at that location, nearby reports (within 500m, last 1 hour), CV output (if photo provided), historical flood likelihood for that area

**Output:**
```json
{
  "report_id": "rpt_001",
  "verification_status": "verified",
  "confidence_score": 0.91,
  "flags": [],
  "estimated_depth": "20-40cm"
}
```

**Verification Rules (rule-based + ML hybrid):**
1. If rainfall > 10mm/hr in the last 2 hours near the location -> boost confidence
2. If 3+ reports within 500m in the last hour -> boost confidence
3. If CV model confirms water in attached photo -> boost confidence
4. If report claims deep flood but no rain and no nearby reports -> flag as suspicious
5. Historical flood hotspot -> boost confidence
6. User trust score (future) -> weight reports accordingly

**Model:**
- Rule-based scoring (weighted sum) as baseline
- Optional: logistic regression or small neural net trained on labeled report data

**Deliverables:**
```
modeling/report_verifier/
├── verifier.py           # Main verification logic
├── rules.py              # Rule definitions & scoring weights
├── scorer.py             # ML-based scoring (if trained)
├── config.yaml           # Rule weights & thresholds
└── README.md
```

---

### Capability 4: Data Scraping Pipeline

**Purpose:** Collect real-world data from public sources to feed the models.

**Target Sources:**

| Source | Data Type | Purpose |
|---|---|---|
| BMKG (cuaca.bmkg.go.id) | Real-time & historical rainfall | Predictive model input |
| OpenStreetMap (Overpass API) | Drainage, land use, roads, waterways | Feature engineering |
| SRTM / USGS EarthExplorer | Elevation (DEM) | Feature engineering |
| Kaggle | Flood image datasets | CV classifier training |
| Google Earth / Sentinel Hub | Satellite imagery (optional) | Land cover analysis |
| Local government portals (BPBD Semarang) | Historical flood records | Predictive model training |
| Social media / news | Flood reports, images | CV training data + report verification |
| CCTV snapshots (public feeds) | Real-time street images | CV classifier input |

**Implementation:**
- Python scripts using `requests`, `BeautifulSoup`, `selenium` (if JS-rendered)
- BMKG data via their public API or CSV download
- Overpass API queries for OSM data
- Kaggle CLI for dataset downloads
- Rate limiting and caching built in

**Deliverables:**
```
modeling/scraping/
├── bmkg_scraper.py        # Rainfall data from BMKG
├── osm_scraper.py         # OpenStreetMap features via Overpass
├── kaggle_downloader.py   # Flood image datasets
├── news_scraper.py        # News/social media flood reports (optional)
├── dem_downloader.py      # Elevation data
├── utils.py               # Shared: rate limiter, cache, retry logic
├── config.yaml            # Source URLs, API endpoints, rate limits
└── README.md
```

---

### Shared Infrastructure

#### FastAPI Backend
All 3 models exposed as REST endpoints for frontend integration.

**Endpoints:**
```
POST /api/classify-image
  -> Input: image file
  -> Output: CV classifier result

POST /api/predict-flood
  -> Input: area_id or lat/lng + time_window
  -> Output: flood prediction

POST /api/verify-report
  -> Input: report data (location, timestamp, description, photo)
  -> Output: verification result

GET  /api/flood-zones
  -> Output: all current flood zones with risk levels

GET  /api/predictions
  -> Output: all active predictive alerts
```

**Deliverables:**
```
modeling/api/
├── main.py               # FastAPI app, route definitions
├── schemas.py            # Pydantic request/response models
├── dependencies.py       # Model loading, shared state
└── README.md
```

#### Data Directory
```
modeling/data/
├── README.md             # All dataset documentation
├── raw/                  # Unprocessed downloads & scrapes
├── processed/            # Cleaned, feature-engineered data
└── sample/               # Small sample data for quick testing
```

#### Target Directory Structure (Full)
```
modeling/
├── MODELING_PRD.md          # This document
├── README.md                # Setup & usage instructions
├── requirements.txt         # All Python dependencies
├── .env.example             # Template for API keys
├── .gitignore               # Ignore .env, __pycache__, checkpoints, raw data
├── data/
│   ├── README.md
│   ├── raw/
│   ├── processed/
│   └── sample/
├── scraping/
│   ├── bmkg_scraper.py
│   ├── osm_scraper.py
│   ├── kaggle_downloader.py
│   ├── dem_downloader.py
│   ├── news_scraper.py
│   ├── utils.py
│   ├── config.yaml
│   └── README.md
├── cv_classifier/
│   ├── model.py
│   ├── dataset.py
│   ├── train.py
│   ├── infer.py
│   ├── evaluate.py
│   ├── config.yaml
│   ├── checkpoints/
│   └── README.md
├── predictive_model/
│   ├── features.py
│   ├── dataset.py
│   ├── train.py
│   ├── infer.py
│   ├── evaluate.py
│   ├── config.yaml
│   ├── checkpoints/
│   └── README.md
├── report_verifier/
│   ├── verifier.py
│   ├── rules.py
│   ├── scorer.py
│   ├── config.yaml
│   └── README.md
├── api/
│   ├── main.py
│   ├── schemas.py
│   ├── dependencies.py
│   └── README.md
└── notebooks/
    ├── 01_data_exploration.ipynb
    ├── 02_cv_training.ipynb
    ├── 03_predictive_model.ipynb
    └── 04_integration_test.ipynb
```

---

## PART 3: EXECUTION PHASES

### Phase 1 — Data Foundation (Day 1-2)
- [ ] Set up `requirements.txt` and `.env.example`
- [ ] Build BMKG rainfall scraper -> collect 2024-2026 hourly data for Semarang
- [ ] Download OSM data for Semarang (drainage, waterways, land use, roads)
- [ ] Download SRTM DEM elevation tiles for Semarang
- [ ] Download flood image datasets from Kaggle
- [ ] Document all sources in `data/README.md`
- [ ] Start data exploration notebook

### Phase 2 — Models (Day 3-5)
- [ ] Train CV classifier on flood images -> target >80% accuracy, >0.75 F1 per class
- [ ] Engineer features from scraped data (rainfall aggregates, elevation, drainage density)
- [ ] Train predictive model on historical flood + rainfall -> target AUC >0.80
- [ ] Build rule-based report verifier -> test on mock reports
- [ ] Write evaluation scripts for all models

### Phase 3 — API & Integration (Day 5-6)
- [ ] Wrap all models behind FastAPI endpoints
- [ ] Define Pydantic schemas matching frontend expectations
- [ ] Test API locally with mock requests
- [ ] Output format compatible with `SAFEROUTE_DATA` structure

### Phase 4 — Demo & Documentation (Day 7)
- [ ] End-to-end demo: image -> CV result -> map overlay
- [ ] End-to-end demo: rainfall data -> predictive alert
- [ ] End-to-end demo: citizen report -> verification -> map marker
- [ ] Write README with setup, run, and API usage instructions
- [ ] Clean up notebooks for presentation

---

## PART 4: SUCCESS METRICS

| Metric | Target |
|---|---|
| CV classifier accuracy | > 80% on test set |
| CV depth estimation MAE | < 10 cm |
| Predictive model AUC-ROC | > 0.80 |
| Predictive model lead time | 1-3 hours |
| Report verifier precision | > 85% for "verified" class |
| API response time | < 500ms per request |
| Data coverage | >= 6 months historical rainfall for Semarang |
