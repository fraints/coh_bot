"""
screen_reader.py - Perception module for coh_bot.

Captures screen regions and extracts game state information using
template matching and color analysis.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

import cv2
import mss
import numpy as np

import config
from bot.perception.window_detector import WindowDetector
from bot.perception.data_extractor import DataExtractor

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Snapshot of the game state as perceived from the screen."""
    # Player data
    player_hp_pct: float = 1.0
    player_endurance_pct: float = 1.0
    
    # Target data
    has_target: bool = False
    target_type: str = "target__none"
    target_hp_pct: float = 1.0
    target_endurance_pct: float = 1.0
    target_name: str = ""
    target_details: Dict[str, Any] = field(default_factory=dict)
    
    # Overall flags
    enemy_visible: bool = False
    raw_regions: dict = field(default_factory=dict, repr=False)


class ScreenReader:
    """
    Captures and analyses screen regions to produce a ``GameState``.

    Design notes
    ------------
    * All expensive numpy/cv2 work is kept inside this class so the brain
      module never has to think about pixels.
    * Region coordinates live in ``config.REGIONS`` – calibrate them there.
    * Template images are loaded lazily on first use.
    """

    def __init__(self) -> None:
        self._sct = mss.mss()
        self._monitor = self._sct.monitors[config.MONITOR_INDEX]
        self._templates: dict[str, Optional[np.ndarray]] = {}
        
        # Initialize dynamic window detector and data extractor
        ref_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "screenshots", "references")
        self._window_detector = WindowDetector(ref_dir)
        self._data_extractor = DataExtractor()
        self._window_cache: dict[str, Optional[tuple[int, int, int, int]]] = {
            "player": None,
            "target": None
        }
        
        # Track the last target template matched to determine type
        self._last_target_template: str = "target__none"
        
        logger.info("ScreenReader initialised (monitor %d).", config.MONITOR_INDEX)

    def calibrate(self, screenshot: Optional[np.ndarray] = None) -> None:
        """Find window locations and update the region cache."""
        if screenshot is None:
            screenshot = self._grab_full()
            
        self._window_cache["player"] = self._window_detector.find_player_window(screenshot)
        self._window_cache["target"] = self._window_detector.find_target_window(screenshot)
        
        if self._window_cache["player"]:
            logger.info("Calibrated Player window: %s", self._window_cache["player"])
        if self._window_cache["target"]:
            logger.info("Calibrated Target window: %s", self._window_cache["target"])

    def _grab_full(self) -> np.ndarray:
        """Grab the full game window/monitor."""
        return self._grab(self._monitor["left"], self._monitor["top"], self._monitor["width"], self._monitor["height"])

    # ── Public API ────────────────────────────────────────────────────────────

    def capture(self) -> GameState:
        """Capture the current screen and return a fresh ``GameState``."""
        # Update window locations
        self.calibrate()

        raw: dict[str, np.ndarray] = {}
        state = GameState()

        # Extract Player Data
        p_cache = self._window_cache["player"]
        if p_cache:
            px, py, pw, ph = p_cache
            player_img = self._grab(px, py, pw, ph)
            raw["player_window"] = player_img
            
            p_data = self._data_extractor.extract_player_data(player_img)
            state.player_hp_pct = p_data.get("hp_pct", 1.0)
            state.player_endurance_pct = p_data.get("endurance_pct", 1.0)

        # Extract Target Data
        t_cache = self._window_cache["target"]
        if t_cache:
            tx, ty, tw, th = t_cache
            target_img = self._grab(tx, ty, tw, th)
            raw["target_window"] = target_img
            
            # Use WindowDetector to find the specific target type
            target_type = self._window_detector._last_matched_target_type if hasattr(self._window_detector, "_last_matched_target_type") else "target__unknown"
            state.target_type = target_type
            state.has_target = (target_type != "target__none")

            if state.has_target:
                t_data = self._data_extractor.extract_target_data(target_img, target_type)
                state.target_hp_pct = t_data.get("hp_pct", 1.0)
                state.target_endurance_pct = t_data.get("endurance_pct", 1.0)
                state.target_name = t_data.get("name", "")
                state.target_details = t_data

        # Enemy nearby (center area) - legacy logic
        enemy_reg = config.REGIONS.get("enemy_nearby")
        if enemy_reg:
            l, t, w, h = enemy_reg
            if w > 0:
                raw["enemy_nearby"] = self._grab(l, t, w, h)
                state.enemy_visible = self._detect_enemy(raw.get("enemy_nearby"))

        state.raw_regions = raw
        logger.debug("GameState updated")
        return state

    def load_template(self, name: str, path: str) -> None:
        """Load a template image from *path* and cache it under *name*."""
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Could not load template '%s' from %s", name, path)
        self._templates[name] = img

    def find_template(self, region_img: np.ndarray, template_name: str) -> bool:
        """Return True if *template_name* is found in *region_img*."""
        tmpl = self._templates.get(template_name)
        if tmpl is None or region_img is None:
            return False
        result = cv2.matchTemplate(region_img, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return bool(max_val >= config.TEMPLATE_MATCH_THRESHOLD)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _grab(self, left: int, top: int, width: int, height: int) -> np.ndarray:
        """Capture a screen sub-region and return as a BGR numpy array."""
        mon = {"left": left, "top": top, "width": width, "height": height}
        sct_img = self._sct.grab(mon)
        return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)

    def _parse_hp_bar(self, region: Optional[np.ndarray]) -> float:
        """
        Estimate HP percentage from a colour-coded bar region.

        Strategy: Count pixels whose green channel exceeds a threshold
        (full HP = green, low HP = red/orange in CoH). Returns 1.0 if
        the region is unavailable (safe default).
        """
        if region is None or region.size == 0:
            return 1.0

        # CoH HP bars are green at full health, grade through yellow/red.
        # We look for pixels where green > 120 and green dominates over red.
        g = region[:, :, 1].astype(np.int16)
        r = region[:, :, 2].astype(np.int16)
        healthy_mask = (g > 120) & (g > r + 30)
        total_pixels = region.shape[1]  # width of the bar
        if total_pixels == 0:
            return 1.0
        hp_pct = float(np.sum(healthy_mask.any(axis=0))) / total_pixels
        return max(0.0, min(1.0, hp_pct))

    def _detect_target(self, region: Optional[np.ndarray]) -> bool:
        """
        Returns True if a target box is visible.

        Simple heuristic: check if the target name region has non-background
        pixels (i.e., any bright text present).
        """
        if region is None or region.size == 0:
            return False
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        return bool(np.sum(thresh) > 500)

    def _detect_enemy(self, region: Optional[np.ndarray]) -> bool:
        """
        Placeholder: returns True if an enemy nameplate colour is detected.

        Extend this with template matching against known enemy nameplates.
        """
        if region is None or region.size == 0:
            return False
        # Heuristic: CoH enemy nameplates use a red/orange tint.
        r = region[:, :, 2].astype(np.int16)
        g = region[:, :, 1].astype(np.int16)
        b = region[:, :, 0].astype(np.int16)
        enemy_pixels = np.sum((r > 180) & (r > g + 50) & (r > b + 50))
        return bool(enemy_pixels > 200)
