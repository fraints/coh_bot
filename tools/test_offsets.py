import cv2
import numpy as np

img = cv2.imread('tests/screenshots/references/team/team3.png')

print("--- Team3 Members ---")
y_found = []
for y in range(25, 300):
    row = img[y, 9:200]
    # Bright pixels that form a line
    bright_pixels = np.where((row[:, 1] > 100) & (row[:, 0] < 150))[0]
    
    if len(bright_pixels) > 50:
        if not y_found or y - y_found[-1] > 10:
            y_found.append(y)
            print(f"Member found at y={y}, Green starts at x={9+bright_pixels[0]}")

