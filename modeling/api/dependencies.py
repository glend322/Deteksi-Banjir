"""
FastAPI Dependencies — Model Loading & Shared State
"""
import logging
from pathlib import Path

import torch

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
CHECKPOINT_DIR = ROOT_DIR / "checkpoints"

_cv_model = None
_cv_device = None


def get_cv_model():
    global _cv_model, _cv_device

    if _cv_model is not None:
        return _cv_model, _cv_device

    from cv_model import FloodClassifier

    _cv_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_path = CHECKPOINT_DIR / "best.pt"

    if ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location=_cv_device, weights_only=False)
        backbone = ckpt.get("backbone", "resnet50")
        _cv_model = FloodClassifier(num_classes=2, pretrained=False, backbone=backbone)
        _cv_model.load_state_dict(ckpt["model_state_dict"])
        logger.info(f"CV model loaded from {ckpt_path}")
    else:
        logger.warning("No checkpoint found, using pretrained model")
        _cv_model = FloodClassifier(num_classes=2, pretrained=True, backbone="mobilenet_v3_small")

    _cv_model.to(_cv_device)
    _cv_model.eval()

    return _cv_model, _cv_device
