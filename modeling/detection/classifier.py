"""
Classifier — Klasifikasi Tingkat Banjir + Penyebab

Maps depth estimate + cause detection to classification:
  - dangkal  : < 20 cm
  - sedang   : 20-40 cm
  - dalam    : > 40 cm

Cause text:
  - river detected → "sungai meluap"
  - trash detected → "sampah menyumbat saluran"
  - both → "sungai meluap dan sampah menyumbat"
  - none → "genangan air hujan"

Output: "Daerah {nama_daerah} banjir tingkat {classification}. Penyebab {cause}."
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CLASSIFICATION_THRESHOLDS = {
    "dangkal": (0, 20),
    "sedang": (20, 40),
    "dalam": (40, 999),
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
    cause_text: str
    river_detected: bool
    trash_detected: bool


def classify_flood(depth_cm: float, area_name: str, cause_text: str = "genangan air hujan",
                   river_detected: bool = False, trash_detected: bool = False) -> ClassificationResult:
    """
    Classify flood severity based on depth and cause.

    Args:
        depth_cm: estimated water depth in centimeters
        area_name: name of the area (e.g. "Kaligawe, Genuk")
        cause_text: human-readable cause text
        river_detected: whether river was detected
        trash_detected: whether trash was detected

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

    notification = f"Daerah {area_name} banjir tingkat {classification}. Penyebab {cause_text}."

    if depth_cm > 0:
        logger.info(f"[Classifier] depth={depth_cm:.1f}cm -> {classification} | cause={cause_text} | {notification}")

    return ClassificationResult(
        classification=classification,
        status=status,
        status_label=status_label,
        color=color,
        notification=notification,
        depth_cm=depth_cm,
        cause_text=cause_text,
        river_detected=river_detected,
        trash_detected=trash_detected,
    )
