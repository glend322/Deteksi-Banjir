# CV Flood Image Classifier

Detects flooding from images and estimates water depth.

## Classes
| 0 | normal | No flooding |
|---|---|---|
| 1 | waspada | Minor water accumulation |
| 2 | tergenang | Significant flooding |
| 3 | tidak_dapat_dilalui | Severe, road impassable |

## Usage

```bash
# Training
python train.py --config config.yaml --data-dir ../data/raw/kaggle

# Inference
python infer.py --image path/to/image.jpg --checkpoint checkpoints/best.pt
```
