"""
Generate Dummy Checkpoint

Creates a pre-trained checkpoint for demo/testing purposes.
This allows the pipeline to run without actual training data.

Usage:
  python generate_checkpoint.py
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import torch
from detection.cv_model import FloodClassifier

CHECKPOINT_DIR = ROOT_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    backbone = "mobilenet_v3_small"
    model = FloodClassifier(num_classes=2, pretrained=True, backbone=backbone)
    model.eval()

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "backbone": backbone,
        "num_classes": 2,
        "val_acc": 0.0,
        "epoch": 0,
        "note": "Dummy checkpoint for demo. Train with real data for production.",
    }

    save_path = CHECKPOINT_DIR / "best.pt"
    torch.save(checkpoint, save_path)
    print(f"Checkpoint saved to {save_path}")
    print(f"  Backbone: {backbone}")
    print(f"  Classes: 2 (no_flood, flood)")
    print(f"  Note: Use train.py with real flood image data for production model")


if __name__ == "__main__":
    main()
