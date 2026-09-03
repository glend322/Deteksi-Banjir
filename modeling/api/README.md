# Modeling API

FastAPI backend exposing all ML models as REST endpoints.

## Setup

```bash
pip install -r ../requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/classify-image` | Flood detection from image |
| POST | `/api/predict-flood` | Predict flood risk for area |
| POST | `/api/verify-report` | Verify citizen report |
| GET | `/api/flood-zones` | Get all current flood zones |
| GET | `/api/predictions` | Get active predictive alerts |
