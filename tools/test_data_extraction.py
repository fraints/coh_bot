import cv2
import sys
import os
import json
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from bot.perception.screen_reader import ScreenReader
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
    target_type = detector._last_matched_target_type

    results = {
        "player": {},
        "target": {}
    }

    debug_img = screenshot.copy()

    # Extract Player Data
    if player_box:
        x, y, w, h = player_box
        player_img = screenshot[y:y+h, x:x+w]
        p_data = extractor.extract_player_data(player_img)
        results["player"] = p_data
        
        # Draw Player Box (Neon Green)
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(debug_img, "Player", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Draw Bar Boxes
        if p_data.get("debug_boxes"):
            hp_bar = p_data["debug_boxes"].get("hp_bar")
            if hp_bar:
                bx, by, bw, bh = hp_bar
                cv2.rectangle(debug_img, (x + bx, y + by), (x + bx + bw, y + by + bh), (0, 255, 255), 1)
            
            end_bar = p_data["debug_boxes"].get("endurance_bar")
            if end_bar:
                bx, by, bw, bh = end_bar
                cv2.rectangle(debug_img, (x + bx, y + by), (x + bx + bw, y + by + bh), (255, 255, 0), 1)

    # Extract Target Data
    if target_box:
        x, y, w, h = target_box
        target_img = screenshot[y:y+h, x:x+w]
        t_data = extractor.extract_target_data(target_img, target_type)
        results["target"] = t_data
        
        # Draw Target Box (Red)
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(debug_img, f"Target ({target_type})", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Draw Bar Boxes
        if t_data.get("debug_boxes"):
            hp_bar = t_data["debug_boxes"].get("hp_bar")
            if hp_bar:
                bx, by, bw, bh = hp_bar
                cv2.rectangle(debug_img, (x + bx, y + by), (x + bx + bw, y + by + bh), (0, 255, 255), 1)
            
            end_bar = t_data["debug_boxes"].get("endurance_bar")
            if end_bar:
                bx, by, bw, bh = end_bar
                cv2.rectangle(debug_img, (x + bx, y + by), (x + bx + bw, y + by + bh), (255, 255, 0), 1)

    # Print Results
    print("\n--- Extracted Data ---")
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
