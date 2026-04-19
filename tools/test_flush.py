import cv2
import numpy as np
import glob
import os
from bot.perception.window_detector import TemplateWindowDetector

detector = TemplateWindowDetector()
team_tpl_dir = "tests/screenshots/references/team_anchors"
templates = {
    "team_top": detector._load_templates([f"{team_tpl_dir}/window_top.png"]),
    "team_dock": detector._load_templates([f"{team_tpl_dir}/dock_button.png"]),
    "team_close": detector._load_templates([f"{team_tpl_dir}/close_button.png"])
}
detector.templates.update(templates)

for f in sorted(glob.glob('tests/screenshots/references/team/team*.png')):
    img = cv2.imread(f)
    print(f"\n--- {os.path.basename(f)} ---")
    
    closes = detector.detect_all(img, "team_close", nms_x=10, nms_y=10, threshold=0.7)
    if not closes:
        print("No team_close found.")
        continue
    
    cx, cy, cw, ch = closes[0]
    right_window_edge = cx + cw
    
    # scan entire image for bright green
    # just find right-most green pixel in upper area
    green_mask = (img[:, :, 1] > 150) & (img[:, :, 0] < 100) & (img[:, :, 2] < 200)
    y_coords, x_coords = np.where(green_mask)
    
    if len(x_coords) > 0:
        max_green_x = np.max(x_coords)
        print(f"team_close cx={cx}. Max green x={max_green_x}.")
        print(f"Distance cx - max_green_x = {cx - max_green_x}")
    else:
        print("No green found.")
