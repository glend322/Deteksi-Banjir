# Predictive Flood Risk Model

Predicts flood probability 1-3 hours ahead for 12 areas in Kota Semarang using rainfall history, elevation, drainage density, land use, and time features.

## Model

- **Algorithm:** XGBoost (gradient-boosted trees)
- **Task:** Multi-class classification (flood risk level) + regression (water depth)
- **Target AUC-ROC:** > 0.80
- **Lead Time:** 1-3 hours

## Risk Levels

| Probability | Level | Action |
|---|---|---|
| < 0.2 | Normal | No alert |
| 0.2-0.5 | Waspada | Advisory notice |
| 0.5-0.8 | Tergenang | Warning + route rerouting |
| > 0.8 | Tidak Dapat Dilalui | Alert + evacuation |

## Depth Categories

| Range | Vehicle Guidance |
|---|---|
| < 20 cm | Safe for motor & mobil |
| 20-40 cm | Motor risk of stalling |
| 40-70 cm | Only tall/large vehicles |
| > 70 cm | No vehicles recommended |

## Usage

```bash
# 1. Feature engineering (generates processed/ from raw/)
python features.py

# 2. Training (generates checkpoints/)
python train.py

# 3. Evaluation (generates evaluation_results.json)
python evaluate.py

# 4. Inference
python infer.py --area kaligawe
python infer.py --lat -6.942 --lng 110.42
python infer.py --all --time-window 3h
```

## Features (22 total)

**Rainfall (8):** total_precipitation, max_hourly_precipitation, rainy_hours, precipitation_std, precip_sum_1d/3d/7d, precip_max_3d

**Geospatial (8):** elevation_m, lat, lng, drainage_density, nearest_water_body_dist, flood_feature_count, landuse_{residential,commercial,industrial,farmland,forest}_count

**Temporal (4):** day_of_week, month, day_of_year, is_rainy_season

## Areas

12 kecamatan in Kota Semarang: Kaligawe, Genuk, Genuk Indah, Semarang Utara, Tambakrejo, Mangkang, Gayamsari, Simpang Lima, Tembalang, Tugu, Kleweran, Sunter

## Output Format

```json
{
  "area_id": "kaligawe",
  "lat": -6.935,
  "lng": 110.43,
  "flood_probability": 0.82,
  "risk_level": "tergenang",
  "confidence": 0.78,
  "depth_cm": 55.0,
  "depth_range": "40-70cm",
  "time_window": "3h"
}
```

## Files

| File | Purpose |
|---|---|
| features.py | Feature engineering pipeline |
| dataset.py | Data loading, splits, scaler |
| train.py | Model training + checkpointing |
| evaluate.py | Test set metrics |
| infer.py | Prediction for area/coordinates |
| config.yaml | Hyperparameters |
| checkpoints/ | Saved models + scaler |
