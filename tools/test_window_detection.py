import cv2
import sys
import os
import logging

# Add the project root to sys.path to import bot modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.perception.window_detector import WindowDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/test_window_detection.py <screenshot_path>")
        return

    screenshot_path = sys.argv[1]
    if not os.path.exists(screenshot_path):
        print(f"File not found: {screenshot_path}")
        return

    # Initialize detector
    ref_dir = os.path.join("tests", "screenshots", "references")
    detector = WindowDetector(ref_dir)

    # Load screenshot
    img = cv2.imread(screenshot_path)
    if img is None:
        print(f"Could not read image: {screenshot_path}")
        return

    print(f"Analyzing: {screenshot_path}")
    
    # Find windows
    player_box = detector.find_player_window(img)
    target_box = detector.find_target_window(img)

    if player_box:
        print(f"[FOUND] Player window: {player_box}")
    else:
        print("[NOT FOUND] Player window")

    if target_box:
        print(f"[FOUND] Target window: {target_box}")
    else:
        print("[NOT FOUND] Target window")

    # Create debug image
    debug_img = detector.get_debug_image(img, player_box, target_box)
    
    # Save debug image
    base, ext = os.path.splitext(screenshot_path)
    debug_path = f"{base}_debug{ext}"
    cv2.imwrite(debug_path, debug_img)
    print(f"Debug image saved to: {debug_path}")

if __name__ == "__main__":
    main()
