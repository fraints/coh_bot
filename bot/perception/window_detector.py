import cv2
import numpy as np
import logging
import os
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)

class WindowDetector:
    """
    Identifies the coordinates of UI windows in a screenshot using anchor templates.
    Handles translucency by focusing on stable UI elements.
    """

    def __init__(self, references_dir: str):
        self.references_dir = references_dir
        self.templates: Dict[str, np.ndarray] = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """Loads all reference images from the references directory."""
        if not os.path.isdir(self.references_dir):
            logger.error(f"References directory not found: {self.references_dir}")
            return

        for filename in os.listdir(self.references_dir):
            if filename.endswith(".png"):
                name = os.path.splitext(filename)[0]
                path = os.path.join(self.references_dir, filename)
                img = cv2.imread(path)
                if img is not None:
                    self.templates[name] = img
                    logger.debug(f"Loaded template: {name}")

    def find_player_window(self, screenshot: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Finds the player window in the top-right area.
        Returns the most confident match across all player templates.
        """
        h, w = screenshot.shape[:2]
        # Restrict to top 25% of screen and right side
        roi = screenshot[0:h//4, w//2:w]
        offset_x, offset_y = w//2, 0

        best_match = None
        max_confidence = -1.0

        player_templates = [k for k in self.templates.keys() if k.startswith("player__")]
        for t_name in player_templates:
            match_data = self._get_best_match(roi, self.templates[t_name])
            if match_data:
                loc, confidence = match_data
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_match = (loc[0] + offset_x, loc[1] + offset_y, self.templates[t_name].shape[1], self.templates[t_name].shape[0])

        if max_confidence >= 0.65:
            return best_match
        return None

    def find_target_window(self, screenshot: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Finds the target window in the top-left area.
        Returns the most confident match across all target templates.
        """
        h, w = screenshot.shape[:2]
        # Restrict to top 25% of screen and left half
        roi = screenshot[0:h//4, 0:w//2]
        offset_x, offset_y = 0, 0

        best_match = None
        max_confidence = -1.0

        target_templates = [k for k in self.templates.keys() if k.startswith("target__")]
        for t_name in target_templates:
            match_data = self._get_best_match(roi, self.templates[t_name])
            if match_data:
                loc, confidence = match_data
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_match = (loc[0] + offset_x, loc[1] + offset_y, self.templates[t_name].shape[1], self.templates[t_name].shape[0])

        if max_confidence >= 0.65:
            return best_match
        return None

    def _get_best_match(self, roi: np.ndarray, template: np.ndarray) -> Optional[Tuple[Tuple[int, int], float]]:
        """
        Finds the best match for a template in a ROI.
        Returns (location, confidence).
        """
        if roi is None or template is None:
            return None

        # Constant anchor size for comparison: use the top 80x80 area or smaller
        anchor_h, anchor_w = min(80, template.shape[0]), min(80, template.shape[1])
        anchor = template[0:anchor_h, 0:anchor_w]

        if roi.shape[0] < anchor.shape[0] or roi.shape[1] < anchor.shape[1]:
            return None

        res = cv2.matchTemplate(roi, anchor, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        return max_loc, max_val


    def get_debug_image(self, screenshot: np.ndarray, player_box: Optional[Tuple[int, int, int, int]], target_box: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        """Creates a debug copy of the image with colored box outlines."""
        debug_img = screenshot.copy()
        
        # Player window: Neon Green
        if player_box:
            x, y, w, h = player_box
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(debug_img, "PLAYER", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Target window: Red
        if target_box:
            x, y, w, h = target_box
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(debug_img, "TARGET", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        return debug_img
