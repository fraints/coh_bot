"""
Extracts metrics from the player frame region.
"""
from __future__ import annotations

import cv2
import numpy as np

def extract_player_data(screenshot: np.ndarray, anchor_box: tuple[int, int, int, int]) -> dict:
    """
    Given the full screenshot and an anchor block (like the XP wheel or textual buttons),
    isolate the player bars and compute their values.
    """
    x, y, w, h = anchor_box
    # Heuristic for Player Bar when anchoring off XP wheel:
    # The XP wheel is on the right. The HP/End bars stretch out to the left of the XP wheel.
    # We will search within a broader region to find the specific ICON_hp and ICON_end to frame the bars.
    
    # We'll return just the detected sub-regions for now so the debug script can draw them.
    # Let's expand a bounding box to capture the entire expected player frame area.
    # Player frame is roughly 300x120. If anchor is XP wheel, the box is something like:
    # [x - 220, y - 20, 300, 120]
    
    px = max(0, x - 220)
    py = max(0, y - 20)
    pw = 300
    ph = 120
    
    frame_box = (px, py, pw, ph)
    return {"frame_box": frame_box}
