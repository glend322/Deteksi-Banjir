"""
Verifier — False Positive Filter (Stricter)

Ensures CV detection is a genuine flood, not a false positive.
Uses multiple checks to reduce false positives from normal street scenes.
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
        min_confidence: float = 0.95,
        min_depth_cm: float = 25.0,
        min_water_ratio: float = 0.20,
        history_size: int = 10,
    ):
        self.min_confidence = min_confidence
        self.min_depth_cm = min_depth_cm
        self.min_water_ratio = min_water_ratio
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

            water_ratio = self._check_water_area(frame)
            if water_ratio < self.min_water_ratio:
                reasons.append("insufficient_water_area")

            texture_ok = self._check_water_texture(frame)
            if not texture_ok:
                reasons.append("weak_water_texture")

            reflection_check = self._check_water_reflection(frame)
            if not reflection_check:
                reasons.append("no_water_reflection")

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
            and "insufficient_water_area" not in reasons
            and "weak_water_texture" not in reasons
            and "no_water_reflection" not in reasons
        )

        if "weak_water_texture" in reasons:
            confidence_mod -= 0.2
        if "insufficient_water_area" in reasons:
            confidence_mod -= 0.25
        if "no_water_reflection" in reasons:
            confidence_mod -= 0.15
        if "brightness_issue" in reasons:
            confidence_mod -= 0.1

        confidence_mod = max(-0.5, min(0.3, confidence_mod))

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

    def _check_water_area(self, frame: np.ndarray) -> float:
        """Check what percentage of the frame appears to be water surface."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_blue = np.array([85, 30, 30])
        upper_blue = np.array([135, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        lower_green = np.array([35, 30, 30])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        water_mask = cv2.bitwise_or(blue_mask, green_mask)

        kernel = np.ones((5, 5), np.uint8)
        water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_CLOSE, kernel)
        water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_OPEN, kernel)

        water_ratio = float(np.sum(water_mask > 0)) / water_mask.size
        return water_ratio

    def _check_water_texture(self, frame: np.ndarray) -> bool:
        """Check for smooth water texture (low texture variance in water area)."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_blue = np.array([85, 30, 30])
        upper_blue = np.array([135, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        lower_green = np.array([35, 30, 30])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        water_mask = cv2.bitwise_or(blue_mask, green_mask)
        water_ratio = float(np.sum(water_mask > 0)) / water_mask.size

        if water_ratio < 0.05:
            return False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        water_pixels = gray[water_mask > 0]

        if len(water_pixels) < 100:
            return False

        texture_var = float(np.var(water_pixels))
        return texture_var < 1500

    def _check_water_reflection(self, frame: np.ndarray) -> bool:
        """Check for water reflection patterns (smooth gradient in water area)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray, 50, 150)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([85, 30, 30])
        upper_blue = np.array([135, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        lower_green = np.array([35, 30, 30])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        water_mask = cv2.bitwise_or(blue_mask, green_mask)

        kernel = np.ones((5, 5), np.uint8)
        water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_CLOSE, kernel)

        water_edges = cv2.bitwise_and(edges, water_mask)
        water_ratio = float(np.sum(water_mask > 0)) / water_mask.size

        if water_ratio < 0.1:
            return False

        edge_ratio = float(np.sum(water_edges > 0)) / max(np.sum(water_mask > 0), 1)
        return edge_ratio < 0.15

    def _check_temporal_consistency(self, camera_id: str, confidence: float) -> float:
        if camera_id not in self._history:
            self._history[camera_id] = []

        self._history[camera_id].append(confidence)
        if len(self._history[camera_id]) > self._history_size:
            self._history[camera_id] = self._history[camera_id][-self._history_size:]

        recent = self._history[camera_id]
        if len(recent) >= 3:
            avg_recent = sum(recent[-3:]) / 3
            if avg_recent > 0.8:
                return 0.1

        return 0.0
