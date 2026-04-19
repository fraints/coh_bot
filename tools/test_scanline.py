import cv2
import numpy as np

img = cv2.imread('tests/screenshots/references/team/team3.png')

# Members known to be at ly=68 (Leader), ly=99 (Member 2), ly=174 (Member 4 - Dead)
for ly, name in [(68, "Leader"), (99, "Member 2"), (174, "Member 4 (Dead)")]:
    lx = 12
    y = ly + 6 # middle of HP bar
    
    row = img[y, lx:]
    
    diffs = np.abs(np.diff(row.astype(int), axis=0))
    sum_diffs = np.sum(diffs, axis=1)
    
    # print out the first few spikes
    edges = np.where(sum_diffs > 50)[0]
    print(f"--- {name} @ y={y} ---")
    print(f"Strong edges: {edges}")
    
    # We can calculate the exact bound:
    # it's usually the very LAST spike before the known max.
    # Leader is usually max ~180. Member is max ~165.
    max_lookahead = 200 if name == "Leader" else 180
    valid_edges = [e for e in edges if e > 100 and e < max_lookahead]
    
    if valid_edges:
        print(f"Estimated width: {valid_edges[-1]}")
    else:
        print("No valid edges found.")
        
    for i in [160, 161, 162, 170, 171, 172]:
        if i < len(row):
            print(f"  {i:3d}: {row[i]}")
