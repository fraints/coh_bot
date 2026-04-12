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
        self._last_matched_target_type: str = "target__none"
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
        best_type = "target__none"
        max_confidence = -1.0

        target_templates = [k for k in self.templates.keys() if k.startswith("target__")]
        for t_name in target_templates:
            match_data = self._get_best_match(roi, self.templates[t_name])
            if match_data:
                loc, confidence = match_data
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_type = t_name.replace(".png", "")
                    best_match = (loc[0] + offset_x, loc[1] + offset_y, self.templates[t_name].shape[1], self.templates[t_name].shape[0])

        if max_confidence >= 0.65:
            self._last_matched_target_type = best_type
            return best_match
        
        self._last_matched_target_type = "target__none"
        return None

    def find_team_window(self, screenshot: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Finds the team window in the left-middle area.
        """
        h, w = screenshot.shape[:2]
        # Restrict to middle height and left side
        roi = screenshot[h//4:h//4*3, 0:w//4]
        offset_x, offset_y = 0, h//4

        best_match = None
        max_confidence = -1.0

        if "team" in self.templates:
            match_data = self._get_best_match(roi, self.templates["team"])
            if match_data:
                top_loc, top_conf = match_data
                if top_conf >= 0.45:
                    win_x = top_loc[0] + offset_x
                    win_y = top_loc[1] + offset_y
                    
                    # Search for bottom anchor to determine height
                    # Use a generous search region below the top anchor
                    height = 400 # Fallback
                    if "bottom_of_team_window" in self.templates:
                        search_h = min(600, h - win_y)
                        bottom_roi = screenshot[win_y:win_y + search_h, win_x:min(win_x + 400, w)]
                        # We use a lower threshold for the bottom anchor (0.4) as requested
                        # or as needed for translucency.
                        b_match = self._get_best_match(bottom_roi, self.templates["bottom_of_team_window"])
                        if b_match and b_match[1] >= 0.4:
                            # Height is the y-offset within bottom_roi
                            height = b_match[0][1]
                    
                    return (win_x, win_y, 400, int(height))

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


    def get_debug_image(self, screenshot: np.ndarray, 
                        player_box: Optional[Tuple[int, int, int, int]], 
                        target_box: Optional[Tuple[int, int, int, int]],
                        team_box: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
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

        # Team window: Orange/Yellow
        if team_box:
            x, y, w, h = team_box
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 165, 255), 3)
            cv2.putText(debug_img, "TEAM", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2)

        return debug_img
