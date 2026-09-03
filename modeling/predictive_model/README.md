# Predictive Flood Risk Model

Predicts flood probability 1-3 hours ahead using rainfall, history, and terrain data.

## Usage

```bash
# Feature engineering
python features.py --input ../data/raw --output ../data/processed

# Training
python train.py --config config.yaml --data-dir ../data/processed

# Inference
python infer.py --area kaligawe --checkpoint checkpoints/best.pt
```
