# CV Flood Image Classifier

Detects flooding from CCTV or crowd-sourced images and estimates water depth.

## Model

- **Backbone:** MobileNetV3-Small (default), ResNet50, EfficientNet-B0
- **Task:** 4-class classification + depth regression
- **Input:** 224x224 RGB image
- **Parameters:** 1.1M (MobileNetV3-Small)

## Severity Classes

| Class | Label | Meaning |
|---|---|---|
| 0 | normal | No flooding |
| 1 | waspada | Minor water accumulation |
| 2 | tergenang | Significant flooding |
| 3 | tidak_dapat_dilalui | Severe, road impassable |

## Depth Categories

| Range | Vehicle Guidance |
|---|---|
| < 20 cm | Safe for motor & mobil |
| 20-40 cm | Motor risk of stalling |
| 40-70 cm | Only tall/large vehicles |
| > 70 cm | No vehicles recommended |

## Usage

```bash
# Training
python train.py --backbone mobilenet_v3_small --epochs 50 --batch-size 32

# Evaluation
python evaluate.py

# Inference
python infer.py --image path/to/image.jpg
python infer.py --image path/to/image.jpg --checkpoint checkpoints/best.pt
python infer.py --dir path/to/images/
```

## Backbones

| Backbone | Params | Speed (CPU) | Accuracy |
|---|---|---|---|
| mobilenet_v3_small | 1.1M | ~18s/epoch | Good |
| efficientnet_b0 | 5.3M | ~30s/epoch | Better |
| resnet50 | 24.3M | ~60s/epoch | Best |

## Output Format

```json
{
  "image": "path/to/image.jpg",
  "flood_detected": true,
  "severity_class": "tergenang",
  "risk_level": "tergenang",
  "flood_probability": 0.82,
  "confidence": 0.91,
  "depth_estimate_cm": 55.0,
  "depth_range": "40-70cm",
  "probabilities": {
    "normal": 0.02,
    "waspada": 0.16,
    "tergenang": 0.82,
    "tidak_dapat_dilalui": 0.00
  }
}
```

## Files

| File | Purpose |
|---|---|
| model.py | Architecture (backbone + dual heads) |
| dataset.py | Dataset loader + synthetic fallback |
| train.py | Training with AMP, early stopping |
| evaluate.py | Test set metrics |
| infer.py | Single-image inference |
| config.yaml | Hyperparameters |
| checkpoints/ | Saved model weights |

## Data

Place images in folder structure:
```
data/
  normal/
  waspada/
  tergenang/
  tidak_dapat_dilalui/
```

If no images found, pipeline uses synthetic colored-noise images for testing.
