import cv2
import numpy as np

img = cv2.imread('tests/screenshots/references/team/team3.png')
# Leader
roi1 = img[66:66+18, 12:12+220]
# Member
roi2 = img[143:143+18, 11:11+220]

for name, roi in [("leader", roi1), ("member", roi2)]:
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # Sum along columns to find vertical edges
    col_sums = np.sum(edges, axis=0)
    
    # Find the right-most strong edge
    # We expect the width to be at least 100
    strong_edges = np.where(col_sums > 255 * 5)[0]
    right_edges = [x for x in strong_edges if x > 100]
    
    print(f"--- {name} ---")
    if right_edges:
        print(f"Right-most strong edge: {right_edges[-1]}")
        print(f"All strong right edges: {right_edges}")
    else:
        print("No right edges found")
        
    cv2.imwrite(f"/tmp/edges_{name}.png", edges)
