"""
Classifier — Klasifikasi Tingkat Banjir

Maps depth estimate from CV model to classification:
  - dangkal  : < 20 cm
  - sedang   : 20-40 cm
  - dalam    : > 40 cm

Output format: "Daerah {nama_daerah} banjir di tingkat {classification}"
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CLASSIFICATION_THRESHOLDS = {
    "dangkal": (0, 20),
    "sedang": (20, 40),
    "dalam": (40, 999),
}

CLASSIFICATION_LABELS = {
    "dangkal": "dangkal",
    "sedang": "sedang",
    "dalam": "dalam",
}

STATUS_MAP = {
    "dangkal": "watch",
    "sedang": "flooded",
    "dalam": "impassable",
}

STATUS_LABEL_MAP = {
    "dangkal": "Waspada",
    "sedang": "Tergenang",
    "dalam": "Tidak Dapat Dilalui",
}

COLOR_MAP = {
    "dangkal": "#F59E0B",
    "sedang": "#F97316",
    "dalam": "#EF4444",
}


@dataclass
class ClassificationResult:
    classification: str
    status: str
    status_label: str
    color: str
    notification: str
    depth_cm: float


def classify_flood(depth_cm: float, area_name: str) -> ClassificationResult:
    """
    Classify flood severity based on depth.

    Args:
        depth_cm: estimated water depth in centimeters
        area_name: name of the area (e.g. "Kaligawe, Genuk")

    Returns:
        ClassificationResult with all metadata
    """
    if depth_cm < 20:
        classification = "dangkal"
    elif depth_cm < 40:
        classification = "sedang"
    else:
        classification = "dalam"

    status = STATUS_MAP[classification]
    status_label = STATUS_LABEL_MAP[classification]
    color = COLOR_MAP[classification]

    notification = f"Daerah {area_name} banjir di tingkat {classification}"

    logger.info(f"[Classifier] depth={depth_cm:.1f}cm -> {classification} | {notification}")

    return ClassificationResult(
        classification=classification,
        status=status,
        status_label=status_label,
        color=color,
        notification=notification,
        depth_cm=depth_cm,
    )
