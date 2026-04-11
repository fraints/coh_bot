"""
test_perception.py - Unit tests for screen_reader.py.

Uses static numpy arrays to simulate captured screen regions without
requiring a live display.
"""

from __future__ import annotations

import numpy as np
import pytest

from bot.perception.screen_reader import ScreenReader


def _green_bar(width: int = 200, height: int = 20, filled_pct: float = 1.0) -> np.ndarray:
    """
    Create a fake HP bar: left portion is bright green, right is dark.
    Channel order: BGR (as returned by OpenCV).
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)
    filled = int(width * filled_pct)
    img[:, :filled] = (0, 200, 0)   # green in BGR
    return img


def _bright_text_region(width: int = 300, height: int = 25) -> np.ndarray:
    """Region with bright white pixels, simulating a target name label."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[5:20, 10:100] = (255, 255, 255)  # white text area
    return img


def _dark_region(width: int = 300, height: int = 25) -> np.ndarray:
    """Uniform dark region – no target, no enemy."""
    return np.zeros((height, width, 3), dtype=np.uint8)


def _enemy_nameplate_region(width: int = 500, height: int = 400) -> np.ndarray:
    """Region with a cluster of red pixels simulating an enemy nameplate."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Paint a stripe of red pixels (enough to exceed the 200-pixel threshold)
    img[50:55, 100:250] = (0, 0, 220)  # BGR: red in the R channel
    return img


class TestHpBarParsing:
    def setup_method(self):
        self.reader = ScreenReader.__new__(ScreenReader)  # skip __init__

    def test_full_health_bar(self):
        bar = _green_bar(filled_pct=1.0)
        pct = self.reader._parse_hp_bar(bar)
        assert pct == pytest.approx(1.0, abs=0.05)

    def test_half_health_bar(self):
        bar = _green_bar(filled_pct=0.5)
        pct = self.reader._parse_hp_bar(bar)
        assert 0.45 <= pct <= 0.55

    def test_empty_health_bar(self):
        bar = np.zeros((20, 200, 3), dtype=np.uint8)  # fully dark / red
        pct = self.reader._parse_hp_bar(bar)
        assert pct == pytest.approx(0.0, abs=0.05)

    def test_none_region_returns_full(self):
        assert self.reader._parse_hp_bar(None) == 1.0


class TestTargetDetection:
    def setup_method(self):
        self.reader = ScreenReader.__new__(ScreenReader)

    def test_detects_target_when_text_present(self):
        region = _bright_text_region()
        assert self.reader._detect_target(region) is True

    def test_no_target_in_dark_region(self):
        region = _dark_region()
        assert self.reader._detect_target(region) is False

    def test_none_region_returns_false(self):
        assert self.reader._detect_target(None) is False


class TestEnemyDetection:
    def setup_method(self):
        self.reader = ScreenReader.__new__(ScreenReader)

    def test_detects_red_nameplate(self):
        region = _enemy_nameplate_region()
        assert self.reader._detect_enemy(region) is True

    def test_no_enemy_in_dark_region(self):
        region = _dark_region(width=500, height=400)
        assert self.reader._detect_enemy(region) is False

    def test_none_region_returns_false(self):
        assert self.reader._detect_enemy(None) is False
