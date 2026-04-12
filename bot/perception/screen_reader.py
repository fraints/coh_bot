import time
import cv2
import mss
import numpy as np
import logging
from typing import Optional

import config
from bot.perception.window_detector import WindowDetector
from bot.perception.data_extractor import DataExtractor
from bot.perception.types import GameState

logger = logging.getLogger(__name__)

class ScreenReader:
    def __init__(self, references_dir: str):
        self.sct = mss.mss()
        self.window_detector = WindowDetector(references_dir)
        self.data_extractor = DataExtractor()
        self.last_state: Optional[GameState] = None

    def capture(self) -> GameState:
        """Captures the screen and extracts all relevant game data."""
        monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080} # Default
        sct_img = self.sct.grab(monitor)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 1. Detect Window Locations
        player_box = self.window_detector.find_player_window(img)
        target_box = self.window_detector.find_target_window(img)
        team_box = self.window_detector.find_team_window(img)

        # 2. Extract Data
        state = GameState(timestamp=time.time())

        if player_box:
            px, py, pw, ph = player_box
            player_img = img[py:py+ph, px:px+pw]
            p_data = self.data_extractor.extract_player_data(player_img)
            state.player_hp_pct = p_data.get("hp_pct", 1.0)
            state.player_endurance_pct = p_data.get("endurance_pct", 1.0)

        if target_box:
            tx, ty, tw, th = target_box
            target_img = img[ty:ty+th, tx:tx+tw]
            t_data = self.data_extractor.extract_target_data(target_img, self.window_detector._last_matched_target_type)
            state.target_type = t_data.get("type", "target__none")
            state.target_name = t_data.get("name")
            state.target_hp_pct = t_data.get("hp_pct")
            state.target_endurance_pct = t_data.get("endurance_pct")
            state.target_level = t_data.get("level")
            state.target_rank = t_data.get("rank")
            state.target_archetype = t_data.get("archetype")
            state.target_origin = t_data.get("origin")
            state.target_enemy_type = t_data.get("enemy_type")
            state.target_super_group = t_data.get("super_group")

        if team_box:
            tmx, tmy, tmw, tmh = team_box
            team_img = img[tmy:tmy+tmh, tmx:tmx+tmw]
            team_data = self.data_extractor.extract_team_data(team_img, self.window_detector.templates)
            state.team_members = team_data

        # 3. Debugging
        if config.DEBUG_MODE:
            debug_img = self.window_detector.get_debug_image(img, player_box, target_box, team_box)
            cv2.imwrite("debug_perception.png", debug_img)

        self.last_state = state
        return state
