import cv2
import numpy as np

img = cv2.imread('tests/screenshots/references/team/team3.png')

# In team3.png, Team Window is at tx=9, ty=1, tw=212, th=314

# Let's find the leader HP y-coordinate by scanning down from ty=1
# The leader's HP bar has bright green/yellow/red.
print("--- Scanning Team3 for Bars ---")
for y in range(30, 200, 5):
    row = img[y, 9:9+212]
    green_pixels = np.where((row[:, 1] > 150) & (row[:, 0] < 100))[0]
    if len(green_pixels) > 20:
        print(f"y={y}: Strong green found from x={9+green_pixels[0]} to {9+green_pixels[-1]}. Length = {green_pixels[-1] - green_pixels[0]}")
        
        # Let's print a few pixels around the start and end
        start_x = 9 + green_pixels[0]
        end_x = 9 + green_pixels[-1]
        
        print(f"  Pixels just before start:")
        for dx in range(-5, 5):
            print(f"    {start_x+dx}: {img[y, start_x+dx]}")
            
        print(f"  Pixels exactly at end:")
        for dx in range(-5, 5):
            print(f"    {end_x+dx}: {img[y, end_x+dx]}")
            
        break # Just print the first one (leader)

for y in range(90, 200, 5):
    row = img[y, 9:9+212]
    green_pixels = np.where((row[:, 1] > 150) & (row[:, 0] < 100))[0]
    if len(green_pixels) > 20:
        print(f"y={y}: Strong green found from x={9+green_pixels[0]} to {9+green_pixels[-1]}. Length = {green_pixels[-1] - green_pixels[0]}")
        break

