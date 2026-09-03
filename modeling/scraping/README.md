# Data Scraping Pipeline

Collects data from BMKG, OpenStreetMap, Kaggle, and other public sources.

## Usage

```bash
# Scrape BMKG rainfall data
python bmkg_scraper.py --start-date 2024-01-01 --end-date 2026-09-01

# Download OSM features for Semarang
python osm_scraper.py

# Download Kaggle flood datasets
python kaggle_downloader.py

# Download DEM elevation tiles
python dem_downloader.py
```

## Rate Limiting
All scrapers respect 1 req/sec per domain. Data is cached in `data/raw/`.
