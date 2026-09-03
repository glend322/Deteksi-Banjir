# Modeling

AI/ML backend for SafeRoute flood detection platform.

## Setup

```bash
cd modeling
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in API keys
```

## Structure

| Module | Purpose |
|---|---|
| `cv_classifier/` | Flood detection from images + depth estimation |
| `predictive_model/` | Predict flood risk 1-3 hours ahead |
| `report_verifier/` | Validate crowd-sourced citizen reports |
| `scraping/` | Collect data from BMKG, OSM, Kaggle, etc. |
| `api/` | FastAPI REST endpoints wrapping all models |
| `data/` | Datasets (raw, processed, sample) |
| `notebooks/` | EDA and training notebooks |

## Run API

```bash
cd modeling/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Key Rules

- All code stays in `modeling/` — never edit frontend files
- Models output format compatible with `js/data.js` structure
- API keys via `.env`, never hardcoded
