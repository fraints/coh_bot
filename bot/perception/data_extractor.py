import cv2
import numpy as np
import pytesseract
import logging
import re
from typing import Optional, Tuple, List, Dict, Any

from bot.perception.types import TeamMember

logger = logging.getLogger(__name__)

class DataExtractor:
    """
    Extracts structured data (HP, Endurance, Text) from UI window crops.
    """

    COLOR_RANGES = {
        "player_hp_green": ([40, 100, 100], [80, 255, 255]),
        "player_hp_yellow": ([20, 100, 100], [40, 255, 255]),
        "player_hp_red": ([0, 100, 100], [10, 255, 255]),
        "player_hp_red_wrap": ([160, 100, 100], [180, 255, 255]),
        "player_endurance": ([100, 100, 100], [140, 255, 255]),
        
        "target_hp_red": ([0, 100, 50], [10, 255, 255]),
        "target_hp_red_wrap": ([160, 100, 50], [180, 255, 255]),
        "target_hp_silver": ([0, 0, 150], [180, 30, 220]), # Wards/Grey bars
        "target_endurance": ([100, 50, 50], [130, 255, 255]),
        
        "ui_blue_border": ([100, 100, 50], [130, 255, 255]),
    }

    def __init__(self):
        pass

    def extract_player_data(self, window_img: np.ndarray) -> Dict[str, Any]:
        """Extracts HP and Endurance % from the player window."""
        if window_img is None: return {}
        h, w = window_img.shape[:2]
        roi_hp = window_img[0:h//2, :]
        hp_pct, hp_box, full_width = self._find_bar_pct(roi_hp, ["player_hp_green", "player_hp_yellow", "player_hp_red", "player_hp_red_wrap"])
        end_pct = 1.0
        end_box = None
        if hp_box:
            search_y_start = hp_box[1] + hp_box[3] + 2
            search_y_end = min(search_y_start + 15, h)
            if search_y_start < h:
                roi_end = window_img[search_y_start:search_y_end, :]
                end_pct, sub_box = self._extract_dependent_bar(roi_end, ["player_endurance"], hp_box[0], full_width)
                if sub_box:
                    end_box = (sub_box[0], sub_box[1] + search_y_start, sub_box[2], sub_box[3])
        return {"hp_pct": hp_pct, "endurance_pct": end_pct, "debug_boxes": {"hp_bar": hp_box, "endurance_bar": end_box}}

    def extract_target_data(self, window_img: np.ndarray, target_type: str) -> Dict[str, Any]:
        """Extracts target details."""
        if window_img is None: return {}
        data: Dict[str, Any] = {"type": target_type}
        debug_boxes: Dict[str, Any] = {}
        h, w = window_img.shape[:2]
        if target_type != "target__none":
            hp_pct, hp_box, full_width = self._find_bar_pct(window_img, ["target_hp_red", "target_hp_red_wrap", "target_hp_silver"])
            data["hp_pct"] = hp_pct
            debug_boxes["hp_bar"] = hp_box
            if target_type in ["target__player", "target__enemy"] and hp_box:
                search_y_start = hp_box[1] + hp_box[3] + 2
                search_y_end = min(search_y_start + 20, h)
                if search_y_start < h:
                    roi_end = window_img[search_y_start:search_y_end, :]
                    end_pct, sub_box = self._extract_dependent_bar(roi_end, ["target_endurance"], hp_box[0], full_width)
                    data["endurance_pct"] = end_pct
                    if sub_box:
                        debug_boxes["endurance_bar"] = (sub_box[0], sub_box[1] + search_y_start, sub_box[2], sub_box[3])
        data["debug_boxes"] = debug_boxes
        text_roi = window_img[0:h//2, :]
        processed = self._preprocess_for_ocr(text_roi)
        text = pytesseract.image_to_string(processed, config="--psm 6").strip()
        data["raw_text"] = text
        self._parse_ocr_text(data, text, target_type)
        return data

    def extract_team_data(self, window_img: np.ndarray, templates: Dict[str, np.ndarray]) -> List[TeamMember]:
        """Extracts data for all team members."""
        if window_img is None: return []
        h, w = window_img.shape[:2]
        members = []
        slot_h = 40
        for i in range(8):
            y_start = i * slot_h
            y_end = min(y_start + slot_h, h)
            if y_start >= h - 10: break
            slot_img = window_img[y_start:y_end, :]
            
            is_dead = self._detect_dead_state(slot_img)
            is_leader = False
            if "yellow_star" in templates:
                anchor = templates["yellow_star"]
                if slot_img.shape[0] >= anchor.shape[0] and slot_img.shape[1] >= anchor.shape[1]:
                    res = cv2.matchTemplate(slot_img, anchor, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val > 0.8: is_leader = True

            hp_pct, end_pct = 1.0, 1.0
            found_hp = False
            if not is_dead:
                hp_pct, hp_box, full_width = self._find_bar_pct(slot_img, ["player_hp_green", "player_hp_yellow", "player_hp_red"])
                if hp_box:
                    found_hp = True
                    search_y_start = hp_box[1] + hp_box[3] + 1
                    roi_end = slot_img[search_y_start:min(search_y_start+10, slot_h), :]
                    end_pct, _ = self._extract_dependent_bar(roi_end, ["player_endurance"], hp_box[0], full_width)
            
            name_roi = slot_img[5:slot_h//2 + 5, :]
            processed = self._preprocess_for_ocr(name_roi)
            name = pytesseract.image_to_string(processed, config="--psm 7").strip()
            name = re.sub(r'[^A-Za-z0-9 _-]', '', name).strip()

            if (found_hp or is_dead) and len(name) > 2:
                members.append(TeamMember(
                    name=name,
                    hp_pct=hp_pct if not is_dead else 0.0,
                    endurance_pct=end_pct if not is_dead else 0.0,
                    is_dead=is_dead,
                    is_leader=is_leader
                ))
            elif i > 1 and not is_dead and not found_hp:
                break
        return members

    def _detect_dead_state(self, slot_img: np.ndarray) -> bool:
        hsv = cv2.cvtColor(slot_img, cv2.COLOR_BGR2HSV)
        # Increased threshold to 500 pixels for grey silhouette
        mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 50, 200]))
        return np.count_nonzero(mask) > 500

    def _find_bar_pct(self, img: np.ndarray, color_keys: List[str], min_y: int = 0) -> Tuple[float, Optional[Tuple[int, int, int, int]], int]:
        if img is None or img.size == 0: return 1.0, None, 0
        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = np.zeros((h, w), dtype=np.uint8)
        for key in color_keys:
            if key in self.COLOR_RANGES:
                lower, upper = self.COLOR_RANGES[key]
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, np.array(lower), np.array(upper)))
        if min_y > 0: mask[0:min_y, :] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_contour = None
        max_area = 0
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw > 15 and bh > 1 and bw > 3 * bh:
                if bw * bh > max_area:
                    max_area = bw * bh
                    best_contour = (bx, by, bw, bh)
        if not best_contour: return 1.0, None, 0
        bx, by, bw, bh = best_contour
        frame_y = by + bh // 2
        row_mask = cv2.inRange(hsv[frame_y, :].reshape(1, -1, 3), np.array(self.COLOR_RANGES["ui_blue_border"][0]), np.array(self.COLOR_RANGES["ui_blue_border"][1]))[0]
        blue_indices = np.where(row_mask > 0)[0]
        container_start, container_end = 0, w
        if len(blue_indices) >= 2:
            left_side = blue_indices[blue_indices < bx]
            right_side = blue_indices[blue_indices > bx + bw]
            c_start = left_side[-1] + 1 if len(left_side) > 0 else 0
            c_end = right_side[0] - 1 if len(right_side) > 0 else w
            container_start, container_end = c_start + 2, c_end - 2
        else: container_end = container_start + (180 if "target" in color_keys[0] else 290)
        full_width = max(bw, container_end - container_start)
        return min(1.0, bw / full_width), best_contour, int(full_width)

    def _extract_dependent_bar(self, roi: np.ndarray, color_keys: List[str], expected_x: int, full_width: int) -> Tuple[float, Optional[Tuple[int, int, int, int]]]:
        if roi is None or roi.size == 0 or full_width <= 0: return 1.0, None
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for key in color_keys:
            if key in self.COLOR_RANGES:
                lower, upper = self.COLOR_RANGES[key]
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, np.array(lower), np.array(upper)))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_cnt = None
        min_dist = 999
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw > 10 and bh > 1:
                dist = abs(bx - expected_x)
                if dist < min_dist: min_dist, best_cnt = dist, (bx, by, bw, bh)
        if not best_cnt: return 0.0, None
        return min(1.0, best_cnt[2] / full_width), best_cnt

    def _preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3,3), 0)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _parse_ocr_text(self, data: Dict[str, Any], text: str, target_type: str):
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines: return
        data["name"] = lines[0]
        for line in lines[1:]:
            if "<" in line and ">" in line:
                start, end = line.find("<"), line.find(">")
                val = line[start+1:end].strip()
                data["enemy_type" if target_type == "target__enemy" else "super_group"] = val
            if "Level" in line or "Lvl" in line:
                match = re.search(r'(Level|Lvl)\s*(\d+)', line)
                if match: data["level"] = int(match.group(2))
            for kw in ["Blaster", "Tanker", "Scrapper", "Defender", "Controller", "Brute", "Stalker", "Mastermind", "Kheldian", "Spider", "Widow"]:
                if kw in line: data["archetype"] = kw
            for kw in ["Minion", "Lieutenant", "Boss", "Elite Boss", "Archvillain", "Hero", "Small", "Medium", "Large"]:
                if kw in line: data["rank"] = kw
            for kw in ["Magic", "Science", "Mutation", "Natural", "Technology"]:
                if kw in line: data["origin"] = kw
