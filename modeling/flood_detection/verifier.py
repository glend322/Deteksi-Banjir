"""
Verifier — False Positive Filter

Ensures CV detection is a genuine flood, not a false positive
 caused by shadows, dark images, small puddles, etc.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    is_genuine_flood: bool
    confidence_modifier: float
    reasons: list[str] = field(default_factory=list)


class FalsePositiveFilter:
    """Rule-based false positive filter for flood detection."""

    def __init__(
        self,
        min_confidence: float = 0.5,
        min_depth_cm: float = 5.0,
        history_size: int = 10,
    ):
        self.min_confidence = min_confidence
        self.min_depth_cm = min_depth_cm
        self._history: dict[str, list[float]] = {}
        self._history_size = history_size

    def filter(
        self,
        frame: Optional[np.ndarray],
        cv_result: dict,
        camera_id: str,
    ) -> VerificationResult:
        """
        Run false positive checks on a detection.

        Args:
            frame: BGR image (numpy array) from CCTV
            cv_result: Output from CV model (flood_detected, depth_estimate_cm, confidence)
            camera_id: Unique camera identifier for history tracking

        Returns:
            VerificationResult with is_genuine_flood, confidence_modifier, and reasons
        """
        reasons = []
        confidence_mod = 0.0

        if not cv_result.get("flood_detected", False):
            return VerificationResult(
                is_genuine_flood=False,
                confidence_modifier=0.0,
                reasons=["no_flood_detected"],
            )

        confidence = cv_result.get("confidence", 0.0)
        depth_cm = cv_result.get("depth_estimate_cm", 0.0)

        if confidence < self.min_confidence:
            reasons.append("low_confidence")

        if depth_cm < self.min_depth_cm:
            reasons.append("depth_too_low")

        if frame is not None:
            brightness_issue = self._check_brightness(frame)
            if brightness_issue:
                reasons.append(brightness_issue)

            texture_check = self._check_water_texture(frame)
            if not texture_check:
                reasons.append("weak_water_texture")

        hist_boost = self._check_temporal_consistency(camera_id, confidence)
        if hist_boost > 0:
            reasons.append("temporal_consistency_boost")
            confidence_mod += hist_boost

        is_genuine = (
            cv_result.get("flood_detected", False)
            and confidence >= self.min_confidence
            and depth_cm >= self.min_depth_cm
            and "low_confidence" not in reasons
            and "depth_too_low" not in reasons
        )

        if "weak_water_texture" in reasons:
            confidence_mod -= 0.15

        if "brightness_issue" in reasons:
            confidence_mod -= 0.1

        confidence_mod = max(-0.3, min(0.3, confidence_mod))

        if reasons:
            logger.debug(f"[Verifier] {camera_id}: reasons={reasons}, mod={confidence_mod:.2f}")

        return VerificationResult(
            is_genuine_flood=is_genuine,
            confidence_modifier=confidence_mod,
            reasons=reasons,
        )

    def _check_brightness(self, frame: np.ndarray) -> Optional[str]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))

        if mean_brightness < 30:
            return "too_dark"
        elif mean_brightness > 240:
            return "too_bright"
        return None

    def _check_water_texture(self, frame: np.ndarray) -> bool:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_blue = np.array([85, 30, 30])
        upper_blue = np.array([135, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        lower_green = np.array([35, 30, 30])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        water_mask = cv2.bitwise_or(blue_mask, green_mask)
        water_ratio = float(np.sum(water_mask > 0)) / water_mask.size

        return water_ratio > 0.05

    def _check_temporal_consistency(self, camera_id: str, confidence: float) -> float:
        if camera_id not in self._history:
            self._history[camera_id] = []

        self._history[camera_id].append(confidence)
        if len(self._history[camera_id]) > self._history_size:
            self._history[camera_id] = self._history[camera_id][-self._history_size:]

        recent = self._history[camera_id]
        if len(recent) >= 3:
            avg_recent = sum(recent[-3:]) / 3
            if avg_recent > 0.7:
                return 0.1

        return 0.0
