import pytest
import cv2
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.perception.window_detector import WindowDetector
from bot.perception.screen_reader import ScreenReader

@pytest.fixture
def detector():
    ref_dir = os.path.join("tests", "screenshots", "references")
    return WindowDetector(ref_dir)

@pytest.mark.parametrize("screenshot_name, expected_player, expected_target", [
    ("Fallen_Gunner_target_mid_hp.png", True, True),
    ("no_target_full_hp.png", True, True),
    ("Double_Tap_Tom_target_lowish_hp.png", True, True),
    ("Howard_npc_target_critical_hp.png", True, True),
])
def test_window_detection(detector, screenshot_name, expected_player, expected_target):
    screenshot_path = os.path.join("tests", "screenshots", screenshot_name)
    img = cv2.imread(screenshot_path)
    assert img is not None, f"Could not load {screenshot_path}"

    player_box = detector.find_player_window(img)
    target_box = detector.find_target_window(img)

    if expected_player:
        assert player_box is not None, f"Player window not found in {screenshot_name}"
        assert player_box[2] > 0 and player_box[3] > 0
    
    if expected_target:
        assert target_box is not None, f"Target window not found in {screenshot_name}"
        assert target_box[2] > 0 and target_box[3] > 0

def test_screen_reader_integration():
    # Test that ScreenReader uses the detector
    reader = ScreenReader()
    screenshot_path = os.path.join("tests", "screenshots", "Fallen_Gunner_target_mid_hp.png")
    img = cv2.imread(screenshot_path)
    
    # We can't easily mock mss in this environment without complex mocking,
    # but we can call calibrate with a provided screenshot.
    reader.calibrate(img)
    
    assert reader._window_cache["player"] is not None
    assert reader._window_cache["target"] is not None
