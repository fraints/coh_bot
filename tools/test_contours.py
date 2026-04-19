import cv2
import numpy as np
import os
import glob
from bot.perception.window_detector import TemplateWindowDetector

detector = TemplateWindowDetector()
team_tpl_dir = "tests/screenshots/references/team_anchors"
detector.templates.update({
    "team_top": detector._load_templates([f"{team_tpl_dir}/window_top.png"]),
    "team_dock": detector._load_templates([f"{team_tpl_dir}/dock_button.png"]),
    "team_close": detector._load_templates([f"{team_tpl_dir}/close_button.png"])
})

img = cv2.imread('tests/screenshots/references/team/team3.png')

# Find team window 
top = detector.detect_all(img, "team_top", nms_y=20, nms_x=20)
close = detector.detect_all(img, "team_close", nms_x=20)
if top and close:
    tx = top[0][0]
    ty = top[0][1]
    cx, cy, cw, ch = close[0]
    tw = cx + cw - tx
    th = 314 # approx
    
    roi = img[ty:ty+th, tx:tx+tw]
    
    # We want to find rectangles. The bars have distinct borders.
    # Gray scale and edge detect
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Thresholding might work better than edge detection because the bars
    # have a filled color + black area.
    # What if we look for the horizontal lines of the bars?
    out = roi.copy()
    
    edges = cv2.Canny(gray, 20, 100)
    
    # morphological closure to close the bars
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 50 and 5 < h < 25:
            cv2.rectangle(out, (x, y), (x+w, y+h), (0, 255, 0), 1)
            print(f"Contour: x={x}, y={y}, w={w}, h={h}")
            
    cv2.imwrite('/tmp/contours_out.png', out)
