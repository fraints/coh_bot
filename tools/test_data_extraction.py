import cv2
import sys
import os
import json
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from bot.perception.screen_reader import ScreenReader
from bot.perception.types import TeamMember
from bot.perception.window_detector import WindowDetector
from bot.perception.data_extractor import DataExtractor

import logging
logging.basicConfig(level=logging.DEBUG)

def test_extraction(image_path):
    print(f"Analyzing: {image_path}")
    screenshot = cv2.imread(image_path)
    if screenshot is None:
        print(f"Error: Could not load image at {image_path}")
        return

    # Initialize components
    ref_dir = "tests/screenshots/references"
    detector = WindowDetector(ref_dir)
    extractor = DataExtractor()

    # Find windows
    player_box = detector.find_player_window(screenshot)
    target_box = detector.find_target_window(screenshot)
    team_box = detector.find_team_window(screenshot)
    target_type = detector._last_matched_target_type

    results = {
        "player": {},
        "target": {},
        "team": []
    }

    debug_img = screenshot.copy()

    # 1. Player Data
    if player_box:
        x, y, w, h = player_box
        p_data = extractor.extract_player_data(screenshot[y:y+h, x:x+w])
        results["player"] = p_data
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(debug_img, "Player", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # 2. Target Data
    if target_box:
        x, y, w, h = target_box
        t_data = extractor.extract_target_data(screenshot[y:y+h, x:x+w], target_type)
        results["target"] = t_data
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(debug_img, f"Target ({target_type})", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 3. Team Data
    if team_box:
        x, y, w, h = team_box
        team_members = extractor.extract_team_data(screenshot[y:y+h, x:x+w], detector.templates)
        results["team"] = [m.__dict__ for m in team_members]
        
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 165, 255), 2)
        cv2.putText(debug_img, "Team Window", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        
        # Draw member slots
        slot_h = 55
        for i, member in enumerate(team_members):
            sy = y + i * slot_h
            cv2.rectangle(debug_img, (x, sy), (x + w, sy + slot_h), (255, 255, 255), 1)
            status = "DEAD" if member.is_dead else f"HP:{int(member.hp_pct*100)}%"
            leader = " (L)" if member.is_leader else ""
            cv2.putText(debug_img, f"{member.name}{leader} - {status}", (x + 5, sy + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Print Results
    print("\n--- Extracted Data ---")
    # Custom encoder for TeamMember or just use __dict__
    print(json.dumps(results, indent=2, sort_keys=True))

    # Save Debug Image
    debug_path = image_path.replace(".png", "_debug_data.png")
    cv2.imwrite(debug_path, debug_img)
    print(f"\nDebug image saved to: {debug_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/test_data_extraction.py <image_path>")
    else:
        test_extraction(sys.argv[1])
