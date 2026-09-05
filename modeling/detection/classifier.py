"""
Classifier — Klasifikasi Tingkat Banjir + Penyebab

Maps depth classification + cause detection to classification:
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

DEPTH_CLASSIFICATION = {
    "dangkal": 0,
    "sedang": 1,
    "dalam": 2,
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
    depth_label: str
    cause_text: str
    river_detected: bool
    trash_detected: bool


def classify_flood(depth_label: str, area_name: str, cause_text: str = "genangan air hujan",
                   river_detected: bool = False, trash_detected: bool = False) -> ClassificationResult:
    """
    Classify flood severity based on depth classification and cause.

    Args:
        depth_label: depth classification (dangkal/sedang/dalam)
        area_name: name of the area (e.g. "Kaligawe, Genuk")
        cause_text: human-readable cause text
        river_detected: whether river was detected
        trash_detected: whether trash was detected

    Returns:
        ClassificationResult with all metadata
    """
    classification = depth_label

    status = STATUS_MAP.get(classification, "safe")
    status_label = STATUS_LABEL_MAP.get(classification, "Aman")
    color = COLOR_MAP.get(classification, "#10B981")

    notification = f"Daerah {area_name} banjir tingkat {classification}. Penyebab {cause_text}."

    if classification in DEPTH_CLASSIFICATION:
        logger.info(f"[Classifier] depth={classification} | cause={cause_text} | {notification}")

    return ClassificationResult(
        classification=classification,
        status=status,
        status_label=status_label,
        color=color,
        notification=notification,
        depth_label=classification,
        cause_text=cause_text,
        river_detected=river_detected,
        trash_detected=trash_detected,
    )
