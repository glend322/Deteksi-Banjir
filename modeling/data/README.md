# Data Documentation

All datasets used in the modeling pipeline.

---

## Scraped Datasets (Raw)

### Rainfall Data — Open-Meteo API
- **Source:** https://api.open-meteo.com (free, no API key)
- **License:** CC BY 4.0 (Open-Meteo)
- **Size:** 210,528 hourly records, 12 areas
- **Date Range:** 2024-09-03 to 2026-09-03 (2 years)
- **Parameters:** precipitation (mm), rain (mm)
- **Areas:** Kaligawe, Genuk, Semarang Utara, Tambakrejo, Mangkang, Gayamsari, Simpang Lima, Tembalang, Tugu, Genuk Indah, Kleweran, Sunter
- **Files:** `raw/rainfall/semarang_rainfall_historical.csv`, `raw/rainfall/semarang_rainfall_summary.csv`, `raw/rainfall/forecast_*.json`

### Elevation Data — Open-Meteo Elevation API
- **Source:** https://api.open-meteo.com/v1/elevation (free, no API key)
- **License:** CC BY 4.0
- **Size:** 2,025 grid points
- **Resolution:** ~0.5 km grid
- **Elevation Range:** 0m – 235m (mean: 114.43m)
- **Files:** `raw/dem/semarang_elevation_grid.csv`, `raw/dem/elevation_stats.json`

### OpenStreetMap Features — Overpass API
- **Source:** https://overpass-api.de (OpenStreetMap)
- **License:** ODbL (Open Database License)
- **Area:** Kota Semarang bounding box (-7.05 to -6.85 lat, 110.35 to 110.55 lng)
- **Files:**
  - `raw/osm/waterways.csv` — 367 waterways (rivers, canals, drains)
  - `raw/osm/land_use.csv` — 1,877 land use areas
  - `raw/osm/water_bodies.csv` — 234 water bodies
  - `raw/osm/roads.csv` — 23,600 roads
  - `raw/osm/flood_features.csv` — 544 flood-related features
  - `raw/osm/summary.json` — Counts summary

### Kaggle Flood Images
- **Source:** Kaggle (requires API key)
- **Status:** Not downloaded yet (needs KAGGLE_USERNAME and KAGGLE_KEY)
- **Recommended datasets:** ritvik1909/flood-detection, anshitagarwal/flood-image-dataset
- **Files:** `raw/kaggle/` (empty)

---

## Processed Datasets (ML-Ready)

### Daily Features
- **Source:** Derived from rainfall + DEM data
- **Size:** 8,772 rows × 14 columns
- **Rows:** 12 areas × 731 days
- **Features:**
  - `area_id`, `area_name`, `lat`, `lng`, `date`
  - `total_precipitation` — daily total (mm)
  - `max_hourly_precipitation` — peak hourly rainfall
  - `rainy_hours` — hours with rain > 0.5mm
  - `precipitation_std` — hourly variability
  - `precip_sum_1d`, `precip_sum_3d`, `precip_sum_7d` — rolling sums
  - `precip_max_3d` — max hourly precip in last 3 days
  - `elevation_m` — area elevation
- **File:** `processed/daily_features.csv`

### Flood Targets
- **Source:** Synthetic labels based on rainfall thresholds
- **Size:** 8,772 rows
- **Labels:** normal (8,400), waspada (360), tergenang (12)
- **Thresholds:** normal < 20mm, waspada 20-50mm, tergenang 50-80mm, tidak_dapat_dilalui > 80mm
- **File:** `processed/flood_targets.csv`

### Geo Features
- **Source:** OSM + DEM data
- **Size:** 2,025 grid points
- **Features:** elevation, drainage density, water body distance, flood feature count, land use counts
- **File:** `processed/geo_features.csv`

### Area Elevations
- **Source:** DEM data mapped to rainfall areas
- **Size:** 12 areas
- **File:** `processed/area_elevations.csv`

---

## Notes

- **Synthetic targets:** Flood labels are based on rainfall thresholds, not actual flood incidents. For production, replace with real historical flood data from BPBD.
- **BMKG alternative:** For official BMKG historical data, register at https://dataonline.bmkg.go.id (free for last 2 years) or request formal data from UPT BMKG.
- **Class imbalance:** Flood events are rare (12 tergenang out of 8,772 days). Use SMOTE, class weights, or oversampling during training.
