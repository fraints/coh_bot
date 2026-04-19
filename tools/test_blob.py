import cv2
import numpy as np

img = cv2.imread('tests/screenshots/references/team/team3.png')

# team3 team window bounds from previous logs
tx, ty, tw, th = 9, 1, 212, 314

roi = img[ty:ty+th, tx:tx+tw]

# Convert ROI to HSV
hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

# We want to find the whole HP bar. It includes Green/Yellow/Red AND the black background.
# Since separating translucent black from varying game background is hard, let's just find the bright colored parts.
# HP colors: Green, Yellow, Red. Let's just do a broad threshold for "bright" colors.
# Saturation > 50, Value > 50
mask = cv2.inRange(hsv, (0, 50, 50), (180, 255, 255))

cv2.imwrite('/tmp/mask.png', mask)

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

out = roi.copy()
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if w > 50 and h > 5:
        cv2.rectangle(out, (x, y), (x+w, y+h), (0, 255, 0), 1)

cv2.imwrite('/tmp/blob_out.png', out)

