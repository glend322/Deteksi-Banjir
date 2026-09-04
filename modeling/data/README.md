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



## Training Data (data/training/)

### Flood Images
- **Directory:** `training/flood/`
- **Source:** Kaggle flood segmentation dataset
- **Count:** 289 images (224x224)
- **Purpose:** Positive class for CV flood detection model

### Non-Flood Images (Street View)
- **Directory:** `training/nonflood/`
- **Source:** Google Street View dataset (Kaggle: paulchambaz/google-street-view)
- **Count:** 300 images
- **Content:** Street-level images of roads, buildings, urban areas from various cities
- **Selection:** Filtered from 10,000 images based on sharpness, brightness, color diversity, and file size
- **Purpose:** Negative class for CV flood detection model

## Sample Data (data/sample/)

### Test Cameras
- **File:** `test_cameras.json`
- **Content:** 8 CCTV cameras with expected flood detection results
- **Purpose:** Pipeline testing, integration testing

### Flood Zones
- **File:** `flood_zones.json`
- **Content:** 4 sample flood zones with severity levels
- **Purpose:** Route engine testing, map visualization testing

### Test Routes
- **File:** `test_routes.json`
- **Content:** 3 route calculation test scenarios
- **Purpose:** Safe route engine testing
