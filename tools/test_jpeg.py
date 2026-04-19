import cv2
import numpy as np
import os
import glob
from bot.perception.window_detector import TemplateWindowDetector

img = cv2.imread('tests/screenshots/full/team1.jpeg')

if img is None:
    print("Could not load team1.jpeg")
else:
    print("Loaded team1.jpeg")
    
    # Let's find dock and close
    dock_img = cv2.imread('tests/screenshots/references/team/dock_button.png')
    close_img = cv2.imread('tests/screenshots/references/team/close_button.png')
    
    res_dock = cv2.matchTemplate(img, dock_img, cv2.TM_CCOEFF_NORMED)
    res_close = cv2.matchTemplate(img, close_img, cv2.TM_CCOEFF_NORMED)
    
    _, _, _, max_loc_dock = cv2.minMaxLoc(res_dock)
    _, _, _, max_loc_close = cv2.minMaxLoc(res_close)
    
    tx = max_loc_dock[0] - 20
    ty = max_loc_dock[1] - 5
    tw = max_loc_close[0] + 14 - tx + 5
    th = 500 # Just slice down
    
    print(f"Extracted bounds from anchors: tx={tx}, ty={ty}, tw={tw}")
    
    roi = img[ty:ty+th, tx:tx+tw]
    
    slice_hp = cv2.imread('tests/screenshots/references/team/slice_hp.png')
    slice_end = cv2.imread('tests/screenshots/references/team/slice_end.png')
    
    # Template match on ROI
    if slice_hp is not None:
        res = cv2.matchTemplate(roi, slice_hp, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.8)
        pts = list(zip(*loc[::-1]))
        print(f"slice_hp at 0.8 threshold in ROI: {len(pts)} points")
        # Let's print distinct Y coordinates
        ys = sorted(list(set([pt[1] for pt in pts])))
        filtered_ys = []
        for y in ys:
            if not filtered_ys or y - filtered_ys[-1] > 10:
                filtered_ys.append(y)
        print("Filtered Y coordinates for slice_hp:", filtered_ys)
        
    if slice_end is not None:
        res = cv2.matchTemplate(roi, slice_end, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.8)
        pts = list(zip(*loc[::-1]))
        ys = sorted(list(set([pt[1] for pt in pts])))
        filtered_ys = []
        for y in ys:
            if not filtered_ys or y - filtered_ys[-1] > 10:
                filtered_ys.append(y)
        print("Filtered Y coordinates for slice_end:", filtered_ys)
