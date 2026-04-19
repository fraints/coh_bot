from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import os

from bot.models import TeamMember, BoundingBox
from bot.perception.window_detector import TemplateWindowDetector

@dataclass
class TeamMemberLayout:
    """Perception model for a team member's UI position."""
    member_index: int
    hp_bar_box: BoundingBox
    end_bar_box: BoundingBox

class TeamWindowExtractor:
    """
    Extracts team member state and layout from a screenshot.
    """
    def __init__(self, detector: TemplateWindowDetector, reference_dir: str):
        self.detector = detector
        self.reference_dir = reference_dir
        
        # Load slice templates for bar detection
        self.slice_hp = cv2.imread(os.path.join(reference_dir, "team", "slice_hp.png"))
        self.slice_hp_yellow = cv2.imread(os.path.join(reference_dir, "team", "slice_hp_yellow.png"))
        self.slice_end = cv2.imread(os.path.join(reference_dir, "team", "slice_end.png"))

    def extract_team(self, img: np.ndarray) -> List[Tuple[TeamMember, TeamMemberLayout]]:
        """
        Locates the team window and extracts state/layout for all members.
        """
        # 1. Find the window bounds using anchors
        all_docks = self.detector.detect_all(img, "team_dock", nms_x=10, threshold=0.7)
        all_closes = self.detector.detect_all(img, "team_close", nms_x=10, threshold=0.7)
        all_bottoms = self.detector.detect_all(img, "team_bottom", nms_x=10, threshold=0.7)
        
        candidates = []
        TARGET_DIST = 176 # Target distance between dock and close
        
        for d in all_docks:
            for c in all_closes:
                dx = abs(d[0] - c[0])
                if 100 < dx < 250:
                    dist_err = abs(dx - TARGET_DIST)
                    tx_min = d[0] - 15
                    tx_max = c[0] + c[2] + 15
                    
                    has_bottom = False
                    for b in all_bottoms:
                        if tx_min - 20 <= b[0] <= tx_max + 20 and b[1] > d[1]:
                            has_bottom = True
                            break
                    
                    score = dist_err
                    if not has_bottom:
                        score += 500
                        
                    candidates.append({
                        "dock": d, "close": c, "score": score,
                        "tx_min": tx_min, "tx_max": tx_max, "has_bottom": has_bottom
                    })
        
        candidates.sort(key=lambda x: x["score"])
        
        if not candidates or not candidates[0]["has_bottom"]:
            return []
            
        best = candidates[0]
        tx_min, tx_max = best["tx_min"], best["tx_max"]
        ty_min = best["dock"][1] - 5
        
        # Find lowest bottom for window height
        team_bottom_y = ty_min + 600 # Fallback
        best_b = None
        for b in all_bottoms:
            if tx_min - 50 < b[0] < tx_max + 50 and b[1] > ty_min:
                if best_b is None or b[1] > best_b[1]:
                    best_b = b
        if best_b:
            team_bottom_y = best_b[1]
        
        team_bottom_y = min(team_bottom_y, img.shape[0])
        tw, th = tx_max - tx_min, max(50, team_bottom_y - ty_min)
        
        # 2. Extract member states
        roi_x1, roi_y1 = max(0, tx_min), max(0, ty_min)
        roi_x2, roi_y2 = min(img.shape[1], tx_min + tw), min(img.shape[0], ty_min + th)
        roi = img[roi_y1:roi_y2, roi_x1:roi_x2]
        
        ys_hp = []
        ys_end = []
        threshold_slice = 0.75
        
        if self.slice_hp is not None and roi.size > 0:
            res = cv2.matchTemplate(roi, self.slice_hp, cv2.TM_CCOEFF_NORMED)
            ys_hp.extend([pt[1] + roi_y1 for pt in zip(*np.where(res >= threshold_slice)[::-1])])
        if self.slice_hp_yellow is not None and roi.size > 0:
            res = cv2.matchTemplate(roi, self.slice_hp_yellow, cv2.TM_CCOEFF_NORMED)
            ys_hp.extend([pt[1] + roi_y1 for pt in zip(*np.where(res >= threshold_slice)[::-1])])
        if self.slice_end is not None and roi.size > 0:
            res = cv2.matchTemplate(roi, self.slice_end, cv2.TM_CCOEFF_NORMED)
            ys_end.extend([pt[1] + roi_y1 for pt in zip(*np.where(res >= threshold_slice)[::-1])])
            
        ys_hp = sorted(list(set(ys_hp)))
        filtered_ys = []
        for y in ys_hp:
            if not filtered_ys or y - filtered_ys[-1] > 10:
                filtered_ys.append(y)
                
        # Shared bar width calculation
        shared_rx = tx_min + tw - 47
        for (cx, cy, cw, ch) in all_closes:
            if tx_min < cx < tx_min + tw and ty_min < cy < ty_min + 50:
                shared_rx = cx - 22
                break
                
        results = []
        start_y = ty_min + 5 + 34 # ty_min was dock.y - 5, so dock.y + 34
        best_snap = None
        for y in filtered_ys:
            if abs(y - start_y) <= 10:
                best_snap = y
                break
        if best_snap: start_y = best_snap
        
        current_y = float(start_y)
        idx = 0
        while current_y + 26 < team_bottom_y and idx < 8:
            is_leader = (idx == 0)
            status = "Dead"
            for y in filtered_ys:
                if abs(y - current_y) <= 8:
                    status = "Alive"
                    current_y = float(y)
                    break
            
            found_end_y = None
            for ey in ys_end:
                if 18 <= (ey - current_y) <= 24:
                    found_end_y = ey
                    break
            
            bar_start_x = tx_min + 2 if is_leader else tx_min + 14
            bar_width = max(50, shared_rx - bar_start_x)
            hp_box = (bar_start_x, int(current_y), bar_width, 17)
            ey = found_end_y if found_end_y is not None else int(current_y) + 21
            end_box = (bar_start_x, ey, bar_width, 7)
            
            member = TeamMember(is_leader=is_leader, status=status, hp_pct=1.0 if status=="Alive" else 0.0)
            layout = TeamMemberLayout(member_index=idx+1, hp_bar_box=hp_box, end_bar_box=end_box)
            results.append((member, layout))
            
            current_y += 31.5
            idx += 1
            
        return results
