"""
CV Flood Detection Model — Multi-Head CNN Architecture

Three-head CNN backbone:
  - Classification head: flood / no_flood
  - Regression head: water depth estimation (cm)
  - Cause detection head: river / trash (multi-label)

Supports: ResNet50, EfficientNet-B0, MobileNetV3-Small
"""
import torch
import torch.nn as nn
import torchvision.models as models


CLASS_NAMES = ["no_flood", "flood"]
CAUSE_NAMES = ["river", "trash"]
DEPTH_BUCKETS = [(0, 20), (20, 40), (40, 200)]
DEPTH_BUCKET_LABELS = ["dangkal", "sedang", "dalam"]
DEPTH_CLASSES = {"dangkal": 0, "sedang": 1, "dalam": 2}
DEPTH_BUCKET_COLORS = ["#F59E0B", "#F97316", "#EF4444"]

BACKBONE_REGISTRY = {
    "resnet50": (models.resnet50, models.ResNet50_Weights, 2048),
    "efficientnet_b0": (models.efficientnet_b0, models.EfficientNet_B0_Weights, 1280),
    "mobilenet_v3_small": (models.mobilenet_v3_small, models.MobileNet_V3_Small_Weights, 576),
}


class FloodClassifier(nn.Module):
    """CNN backbone with three heads: flood cls, depth cls (3 classes), cause detection."""

    def __init__(self, num_classes: int = 2, num_causes: int = 2, num_depth_classes: int = 3, pretrained: bool = True, backbone: str = "resnet50"):
        super().__init__()
        if backbone not in BACKBONE_REGISTRY:
            raise ValueError(f"Unknown backbone: {backbone}. Choose from {list(BACKBONE_REGISTRY.keys())}")

        model_fn, weights_fn, feature_dim = BACKBONE_REGISTRY[backbone]

        if pretrained:
            self.backbone = model_fn(weights=weights_fn.DEFAULT)
        else:
            self.backbone = model_fn(weights=None)

        if hasattr(self.backbone, "fc"):
            self.backbone.fc = nn.Identity()
        elif hasattr(self.backbone, "classifier"):
            self.backbone.classifier = nn.Identity()

        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

        self.depth_classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(feature_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_depth_classes),
        )

        self.cause_classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(feature_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_causes),
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.backbone(x)
        logits = self.classifier(features)
        depth_logits = self.depth_classifier(features)
        cause_logits = self.cause_classifier(features)
        return {
            "logits": logits,
            "depth_logits": depth_logits,
            "cause_logits": cause_logits,
        }


def depth_to_classification(depth_cm: float) -> str:
    """Map depth in cm to dangkal/sedang/dalam."""
    if depth_cm < 20:
        return "dangkal"
    elif depth_cm < 40:
        return "sedang"
    else:
        return "dalam"


def depth_cm_to_class(depth_cm: float) -> int:
    """Map depth in cm to class index (0=dangkal, 1=sedang, 2=dalam)."""
    if depth_cm < 20:
        return 0
    elif depth_cm < 40:
        return 1
    else:
        return 2


def depth_class_to_bucket(depth_class: int) -> str:
    """Map class index to bucket label."""
    return DEPTH_BUCKET_LABELS[depth_class]


def depth_to_bucket(depth_cm: float) -> str:
    """Map depth in cm to bucket label."""
    for (low, high), label in zip(DEPTH_BUCKETS, DEPTH_BUCKET_LABELS):
        if low <= depth_cm < high:
            return label
    return "dalam"


def classification_to_status(classification: str) -> str:
    """Map classification to frontend status enum."""
    mapping = {
        "dangkal": "watch",
        "sedang": "flooded",
        "dalam": "impassable",
    }
    return mapping.get(classification, "safe")


def classification_to_color(classification: str) -> str:
    """Map classification to map color."""
    mapping = {
        "dangkal": "#F59E0B",
        "sedang": "#F97316",
        "dalam": "#EF4444",
    }
    return mapping.get(classification, "#10B981")


def cause_to_text(cause_probs: dict[str, float], threshold: float = 0.5) -> str:
    """Map cause probabilities to human-readable text."""
    detected = [name for name, prob in cause_probs.items() if prob >= threshold]

    if "river" in detected and "trash" in detected:
        return "sungai meluap dan sampah menyumbat"
    elif "river" in detected:
        return "sungai meluap"
    elif "trash" in detected:
        return "sampah menyumbat saluran"
    else:
        return "genangan air hujan"
