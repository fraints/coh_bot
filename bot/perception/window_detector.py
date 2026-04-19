from __future__ import annotations

import cv2
import numpy as np
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Basic types
BoundingBox = Tuple[int, int, int, int]  # x, y, w, h
WindowKind = str

class WindowDetector:
    """
    Protocol/Base class for window detectors.
    """
    def detect(self, screenshot: np.ndarray) -> Dict[WindowKind, BoundingBox]:
        raise NotImplementedError

class TemplateWindowDetector(WindowDetector):
    """
    Detects windows using template matching on known anchors.
    """
    def __init__(self, templates: Dict[WindowKind, list[np.ndarray]], threshold: float = 0.8):
        self.templates = templates
        self.threshold = threshold
        self.cached_boxes: Dict[WindowKind, BoundingBox] = {}

    def detect(self, screenshot: np.ndarray) -> Dict[WindowKind, BoundingBox]:
        # Based on assumption: Windows don't move. Return cache if full.
        # For our tests, we clear cache to ensure we find it each time, but in prod we wouldn't.
        found_windows = {}

        for kind, tmpl_list in self.templates.items():
            if kind in self.cached_boxes:
                found_windows[kind] = self.cached_boxes[kind]
                continue
                
            best_val = -1
            best_loc = None
            best_tmpl = None
            
            for tmpl in tmpl_list:
                if tmpl is None or tmpl.size == 0: continue
                # Template must be smaller than screenshot
                if tmpl.shape[0] > screenshot.shape[0] or tmpl.shape[1] > screenshot.shape[1]:
                    continue
                    
                res = cv2.matchTemplate(screenshot, tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > best_val:
                    best_val = max_val
                    best_loc = max_loc
                    best_tmpl = tmpl
            
            if best_val >= self.threshold and best_loc is not None and best_tmpl is not None:
                # Based on the kind, the bounding box might be inferred from the anchor.
                # For a generalized approach, we record the anchor's box. The specific extractor
                # will know how to parse the surrounding region based on the anchor.
                w, h = best_tmpl.shape[1], best_tmpl.shape[0]
                box = (best_loc[0], best_loc[1], w, h)
                found_windows[kind] = box
                self.cached_boxes[kind] = box
                logger.debug(f"Found {kind} window at {box} with confidence {best_val:.2f}")

        return found_windows

    def detect_all(self, screenshot: np.ndarray, kind: WindowKind, nms_x: int = 10, nms_y: int = 10, threshold: Optional[float] = None) -> list[BoundingBox]:
        """
        Detects all instances of a specific kind above the threshold.
        """
        if kind not in self.templates:
            return []
            
        thresh = threshold if threshold is not None else self.threshold
        tmpl_list = self.templates[kind]
        all_found = []
        
        for tmpl in tmpl_list:
            if tmpl is None or tmpl.size == 0: continue
            if tmpl.shape[0] > screenshot.shape[0] or tmpl.shape[1] > screenshot.shape[1]:
                continue
                
            res = cv2.matchTemplate(screenshot, tmpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(res >= thresh)
            w, h = tmpl.shape[1], tmpl.shape[0]
            
            for pt in zip(*locs[::-1]): # x, y
                all_found.append((pt[0], pt[1], w, h))
        
        # Simple NMS to remove overlaps
        if not all_found: return []
        
        all_found.sort(key=lambda x: x[1]) # Sort by Y
        final = []
        if all_found:
            final.append(all_found[0])
            for box in all_found[1:]:
                # Check overlap with any already in final
                overlap = False
                for f in final:
                    if abs(box[1] - f[1]) < nms_y and abs(box[0] - f[0]) < nms_x:
                        overlap = True
                        break
                if not overlap:
                    final.append(box)
        return final
