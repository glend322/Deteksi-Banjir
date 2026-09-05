# Data Documentation

## Raw Data (data/raw/)

### Kaggle Flood Prediction Dataset
- **Source:** https://www.kaggle.com/datasets/naiyakhalid/flood-prediction-dataset
- **License:** CC0: Public Domain
- **Files:**
  - `flood.csv`: 50,000 rows x 21 columns (main dataset)
  - `train.csv`: 1,117,957 rows x 22 columns (training split)
  - `test.csv`: 745,305 rows x 21 columns (test split)
  - `sample_submission.csv`: 745,305 rows x 2 columns
- **Columns:** MonsoonIntensity, TopographyDrainage, RiverManagement, Deforestation, Urbanization, ClimateChange, DamsQuality, Siltation, AgriculturalPractices, Encroachments, IneffectiveDisasterPreparedness, DrainageSystems, CoastalVulnerability, Landslides, Watersheds, DeterioratingInfrastructure, PopulationScore, WetlandLoss, InadequatePlanning, PoliticalFactors, FloodProbability
- **Purpose:** Feature engineering for flood risk prediction model

### OSM Data (OpenStreetMap)
- **Source:** Overpass API (https://overpass-api.de/)
- **Bounding Box:** -7.10,110.30,-6.90,110.55 (Semarang area)
- **Files:**
  - `osm_roads.json`: 209,137 elements (roads network)
  - `osm_waterways.json`: 26,777 elements (rivers, streams)
  - `osm_drainage.json`: 2,982 elements (drainage channels)
  - `osm_land_use.json`: 106,781 elements (land use zones)
- **Purpose:** Routing graph, flood risk features, drainage analysis

### BMKG Weather Data
- **Source:** BMKG API (sample data - API returned 404)
- **File:** `bmkg_weather.json`
- **Content:** Current weather + hourly forecast for Semarang
- **Purpose:** Rainfall data for flood prediction

### CCTV Pantau Semarang
- **Source:** https://pantausemar.semarangkota.go.id/
- **Stream:** HLS via https://livepantau.semarangkota.go.id/
- **License:** Government Open Data (Pemkot Semarang)
- **Last scraped:** September 2026
- **Categories:**
  - `rawan_genangan` (UUID: df69dbea-87c9-4d79-9ddc-f388c33f2dc9) — flood-prone areas
  - `sungai` (UUID: 194fd5d9-098f-4dbe-93da-8288c6761bf0) — river monitoring
  - `pompa_air` (UUID: 5b5b7e51-3a2e-446f-8fae-50d8e9e7196d) — water pumps
- **Total cameras:** 77 (as of Sept 2026)
- **Fields:** cctv_id, name, lat, lng, stream_url (HLS .m3u8), category
- **Purpose:** Real-time flood detection input for CV model
- **Scrape rate:** Max 1 req/det per domain (Rule 6)

## Processed Data (data/processed/)

### Road Graph
- **File:** `roads_graph.json` (1.6 MB)
- **Content:** 5,000 road segments with coordinates
- **Fields:** id, name, highway type, coords [[lat, lng], ...]
- **Purpose:** Route calculation engine input

### Waterways Graph
- **File:** `waterways_graph.json` (758 KB)
- **Content:** 635 waterway segments
- **Fields:** id, name, waterway type, coords
- **Purpose:** Flood risk analysis near water bodies

### Drainage Graph
- **File:** `drainage_graph.json` (87 KB)
- **Content:** 134 drainage channel segments
- **Fields:** id, name, type, coords
- **Purpose:** Drainage quality assessment for flood prediction

### Weather Current
- **File:** `weather_current.json`
- **Content:** Current weather conditions + forecast
- **Purpose:** Real-time rainfall input for detection pipeline

### Camera Baselines
- **File:** `camera_baselines.json`
- **Content:** Baseline water levels per CCTV camera
- **Purpose:** False positive filter - compares current water level vs baseline
- **Updated:** Automatically after each scan

## Training Data (data/training/)

### Flood Images
- **Directory:** `training/flood/`
- **Source:** Kaggle flood segmentation dataset
- **Count:** 289 images (224x224)
- **Purpose:** Positive class for CV flood detection model

### Non-Flood Images
- **Directory:** `training/nonflood/`
- **Sources:**
  1. Google Street View dataset (Kaggle: paulchambaz/google-street-view) - 300 images
  2. Real CCTV frames from Pantau Semarang - 48 images (labeled as non-flood baseline)
- **Total Count:** 348 images
- **Purpose:** Negative class for CV flood detection model

### Auto Labels
- **File:** `auto_labels.json`
- **Content:** Auto-generated labels for scraped CCTV frames based on water detection heuristics
- **Note:** Not used for training - actual labels are all non-flood (baseline)
