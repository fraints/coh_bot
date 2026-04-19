import cv2
import glob
import os
import numpy as np
import argparse
import logging
import time
from bot.perception.window_detector import TemplateWindowDetector

def load_templates(paths: list[str]) -> list:
    ret = []
    for p in paths:
        for f in glob.glob(p):
            t = cv2.imread(f)
            if t is not None:
                ret.append(t)
    return ret

def process_image(shot_path: str, detector: TemplateWindowDetector, out_dir: str, profile: bool = False):
    img = cv2.imread(shot_path)
    if img is None:
        print(f"Error: Could not read image {shot_path}")
        return

    print(f"\nProcessing {os.path.basename(shot_path)}", flush=True)
    
    # Skip tiny template images that shouldn't be processed as screenshots
    if img.shape[0] < 80 or img.shape[1] < 80:
        print(f"  Skipping: image too small to be a screenshot ({img.shape[1]}x{img.shape[0]})", flush=True)
        return
    
    t_start = time.perf_counter()
    
    detector.cached_boxes.clear()
    windows = detector.detect(img)
    t_detect = time.perf_counter()
    
    if windows is None:
        print(f"  Skipping {os.path.basename(shot_path)}: Image too small or invalid", flush=True)
        return
    
    # Log all detections
    for k, (x, y, w, h) in windows.items():
        print(f"  [{k}] found at ({x}, {y}) [{w}x{h}]", flush=True)
    
    # Validation & Fallback logic for Player Bar
    icon_hp = windows.get("icon_hp")
    icon_end = windows.get("icon_end")
    
    if icon_hp:
        hx, hy, hw, hh = icon_hp
        
        # Validate icon_end if it exists
        if icon_end:
            ex, ey, ew, eh = icon_end
            if abs(hx - ex) > 20 or ey < hy:
                print(f"  [icon_end] Rejected at ({ex}, {ey}): spatially inconsistent with HP bar", flush=True)
                icon_end = None
                del windows["icon_end"]

        # Fallback for icon_end if missing or rejected
        if not icon_end:
            # Assume end bar is right below HP bar starting point
            ey_fallback = hy + 9
            ex_fallback = hx
            # We'll use the same size as icon_hp if we don't know it
            ew_fallback, eh_fallback = hw, hh
            icon_end = (ex_fallback, ey_fallback, ew_fallback, eh_fallback)
            windows["icon_end"] = icon_end
            print(f"  [icon_end] FALLBACK used at ({ex_fallback}, {ey_fallback})", flush=True)

    t_player = time.perf_counter()
    # --- Target Window Logic ---
    target_box = None
    target_type = "Unknown"
    
    if "target_actions" in windows:
        ax, ay, aw, ah = windows["target_actions"]
        tx, ty = ax, ay - 63 
        target_box = (tx, ty, 237, 90)
    elif "target_corner" in windows:
        ax, ay, aw, ah = windows["target_corner"]
        target_box = (ax, ay, 237, 90)
    elif "target_edge" in windows:
        ax, ay, aw, ah = windows["target_edge"]
        target_box = (ax - 30, ay, 237, 90)
            
    if target_box:
        tx, ty, tw, th = target_box
        print(f"  [Target Window] located at {target_box}", flush=True)
        
        # Classification: Check if indicators are INSIDE the window
        is_none = False
        is_player = False
        
        if "target_none" in windows:
            nx, ny, nw, nh = windows["target_none"]
            # None text is roughly centered [nx: 80:160, ny: 30:60] in 237x90 frame
            if tx <= nx <= tx + tw and ty <= ny <= ty + th:
                is_none = True
                
        if "target_archetype" in windows:
            ax, ay, aw, ah = windows["target_archetype"]
            # Archetype icon is on the right [ax: 180:215, ay: 20:45]
            if tx <= ax <= tx + tw and ty <= ay <= ty + th:
                is_player = True
        
        if is_none:
            target_type = "None"
        elif is_player:
            target_type = "Player"
        elif any(k in ["target_icon_hp", "target_icon_end"] for k in windows):
            # Same check for bars: are they inside the window?
            hp_in = False
            if "target_icon_hp" in windows:
                hx, hy, hw, hh = windows["target_icon_hp"]
                if tx <= hx <= tx + tw and ty <= hy <= ty + th:
                    hp_in = True
            if hp_in:
                target_type = "Enemy"
            else:
                target_type = "NPC/Object"
        else:
            target_type = "NPC/Object"
            
        print(f"  [Target Type] {target_type}", flush=True)

    t_target = time.perf_counter()
    # --- Team Window Logic ---
    team_elements = []
    for k in ["team_top", "team_bottom", "team_dock", "team_close", "chat_top"]:
        if k in windows:
            team_elements.append(windows[k])
            
    team_box = None
    team_box = None
    if team_elements:
        # Use detect_all for dock and close so we can find a matching PAIR on the same window,
        # instead of blindly trusting the single highest-confidence match (which can false positive).
        all_docks = detector.detect_all(img, "team_dock", nms_x=10, threshold=0.7)
        all_closes = detector.detect_all(img, "team_close", nms_x=10, threshold=0.7)
        all_bottoms = detector.detect_all(img, "team_bottom", nms_x=10, threshold=0.7)
        
        candidates = []
        
        # Target distance between dock and close is ~176px
        TARGET_DIST = 176
        
        # Find all dock+close pairs that are within a reasonable range
        for d in all_docks:
            for c in all_closes:
                dx = abs(d[0] - c[0])
                if 100 < dx < 250: # Standard team window range
                    # Score based on proximity to target distance
                    dist_err = abs(dx - TARGET_DIST)
                    
                    # Check if there is an associated team_bottom button in this X range
                    # (Strictly speaking, team_bottom doesn't have to be found, but it's a strong signal)
                    tx_min = d[0] - 15
                    tx_max = c[0] + c[2] + 15
                    
                    has_bottom = False
                    for b in all_bottoms:
                        if tx_min - 20 <= b[0] <= tx_max + 20 and b[1] > d[1]:
                            has_bottom = True
                            break
                    
                    # Store candidate with its score
                    score = dist_err
                    if not has_bottom:
                        score += 500 # Heavy penalty for no bottom bar
                    
                    candidates.append({
                        "dock": d,
                        "close": c,
                        "score": score,
                        "tx_min": tx_min,
                        "tx_max": tx_max,
                        "has_bottom": has_bottom
                    })
                    
        # Sort by best score (lowest)
        candidates.sort(key=lambda x: x["score"])
        
        dock = None
        close = None
        
        # Only accept candidates that have an associated bottom bar (high confidence)
        # or at least a very good distance match if non-optional.
        if candidates and candidates[0]["has_bottom"]:
            best = candidates[0]
            dock = best["dock"]
            close = best["close"]
            tx_min = best["tx_min"]
            tx_max = best["tx_max"]
        else:
            # Fallback to single anchors if NO pair with bottom found, 
            # but ONLY if there's high confidence.
            # In most cases, if there's no bottom bar, it's not a team window.
            tx_min, tx_max = None, None
            
        if tx_min is not None and tx_max is not None:
            # We have valid reliable horizontal bounds! Now determine Y.
            ty_min = dock[1] if dock else close[1]
            ty_min -= 5 # header top cushion
            
            # Find the LOWEST team_bottom for THIS specific window to get the full height
            team_bottom_y = ty_min + 600 # Fallback
            best_b = None
            for b in all_bottoms:
                if tx_min - 50 < b[0] < tx_max + 50 and b[1] > ty_min:
                    if best_b is None or b[1] > best_b[1]:
                        best_b = b
            
            if best_b:
                print(f"  [team_bottom] using match at ({best_b[0]}, {best_b[1]}) for window height", flush=True)
                team_bottom_y = best_b[1]
            
            # Hard ceiling: window can't extend beyond image height
            team_bottom_y = min(team_bottom_y, img.shape[0])
            
            tw = tx_max - tx_min
            th = max(50, team_bottom_y - ty_min)
            team_box = (tx_min, ty_min, tw, th)

    if team_box:
        tx, ty, tw, th = team_box
        print(f"  [Team Window] located at {team_box}", flush=True)
        cv2.rectangle(img, (tx, ty), (tx+tw, ty+th), (0, 255, 255), 2)
        cv2.putText(img, "Team", (tx, ty - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # We need to manually find the members using pure slices instead of large templates
        # owing to JPEG artifacts breaking larger structural matches.
        
        slice_hp = cv2.imread('tests/screenshots/references/team/slice_hp.png')
        slice_hp_yellow = cv2.imread('tests/screenshots/references/team/slice_hp_yellow.png')
        slice_end = cv2.imread('tests/screenshots/references/team/slice_end.png')
        
        # ROI for searching to prevent false positives across the screen
        roi_x1 = max(0, tx)
        roi_y1 = max(0, ty)
        roi_x2 = min(img.shape[1], tx + tw)
        roi_y2 = min(img.shape[0], ty + th)  # Strongly constrained above team_bottom
        roi = img[roi_y1:roi_y2, roi_x1:roi_x2]
        
        ys_hp = []
        ys_end = []
        threshold_slice = 0.75  # slightly relaxed to handle JPEG compression at window edges
        if slice_hp is not None and roi.shape[0] > 0 and roi.shape[1] > 0:
            res = cv2.matchTemplate(roi, slice_hp, cv2.TM_CCOEFF_NORMED)
            ys_hp.extend([pt[1] + roi_y1 for pt in zip(*np.where(res >= threshold_slice)[::-1])])
            
        if slice_hp_yellow is not None and roi.shape[0] > 0 and roi.shape[1] > 0:
            res = cv2.matchTemplate(roi, slice_hp_yellow, cv2.TM_CCOEFF_NORMED)
            ys_hp.extend([pt[1] + roi_y1 for pt in zip(*np.where(res >= threshold_slice)[::-1])])

        if slice_end is not None and roi.shape[0] > 0 and roi.shape[1] > 0:
            res = cv2.matchTemplate(roi, slice_end, cv2.TM_CCOEFF_NORMED)
            ys_end.extend([pt[1] + roi_y1 for pt in zip(*np.where(res >= threshold_slice)[::-1])])
            
        # NMS for exact Ys (filter close duplicates)
        ys_hp = sorted(list(set(ys_hp)))
        filtered_ys = []
        for y in ys_hp:
            if not filtered_ys or y - filtered_ys[-1] > 10:
                filtered_ys.append(y)
                
        # Extrapolate slots mathematically downwards to guarantee we catch completely dead members
        all_members = []
        if team_box is not None:
            # Leader is firmly anchored ~34px below the dock/close button header line
            # (Matches team1/team2 "great" spacing)
            start_y = ty + 34
            
            # Snap to a real HP slice ONLY if it's within a tight tolerance of the expected anchor
            # (Prevents matching Archetype icons or other green noise in the header)
            best_snap = None
            for y in filtered_ys:
                if abs(y - start_y) <= 10:
                    best_snap = y
                    break
            if best_snap:
                start_y = best_snap
                
            current_y = float(start_y)
            idx = 0
            
            while current_y + 26 < team_bottom_y:
                # Limit to 8 max members.
                if idx >= 8:
                    break
                    
                is_leader = (idx == 0)
                status = "Dead"
                
                # Check if this mathematical slot aligns with an active HP slice
                for y in filtered_ys:
                    if abs(y - current_y) <= 8:
                        status = "Alive"
                        current_y = float(y) # Snap to the actual true Y to prevent vertical drift
                        break
                
                # Try to find a matching endurance bar for this slot
                found_end_y = None
                for ey in ys_end:
                    if 18 <= (ey - current_y) <= 24:
                        found_end_y = ey
                        break
                        
                all_members.append((tx, int(current_y), 0, 18, status, is_leader, found_end_y))
                
                # Next slot - 31.5 handles alternating 31 / 32 pixel gaps perfectly
                current_y += 31.5 
                idx += 1
        
        # Find right edge of the bar (flush across all members)
        # It's at a fixed offset from team_close if it exists, else from the right side of window
        shared_rx = tx + tw - 47
        team_close_matches = detector.detect_all(img, "team_close", nms_x=10, threshold=0.7)
        for (cx, cy, cw, ch) in team_close_matches:
            if tx < cx < tx + tw and ty < cy < ty + 50: # Close is near top
                shared_rx = cx - 22
                break
        
        # Draw the members
        for member_idx, (lx, ly, lw, lh, status, is_leader, found_end_y) in enumerate(all_members, 1):
            
            # Left edge
            bar_start_x = tx + 2 if is_leader else tx + 14
            
            bar_width = shared_rx - bar_start_x
            if bar_width < 50:
                bar_width = 160
            
            # HP Bar
            cv2.rectangle(img, (bar_start_x, ly), (bar_start_x + bar_width, ly + 17), (0, 255, 0), 1) # HP Green (17px tall)
            cv2.putText(img, f"M{member_idx}: {status}", (bar_start_x, ly + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
            
            # END Bar: immediately below HP bar
            # If we found an endurance slice, use its Y. Otherwise, use offset.
            # Real offset seems to be around +20 or +21 to be below the HP border.
            ey = found_end_y if found_end_y is not None else ly + 21
            cv2.rectangle(img, (bar_start_x, ey), (bar_start_x + bar_width, ey + 7), (255, 0, 0), 1) # Blue

            print(f"  [Team Member {member_idx}] {status} at ({bar_start_x}, {ly}) end_y={ey} bounds: {bar_width}w", flush=True)

  

    # Annotation
    min_x, min_y = 99999, 99999
    max_x, max_y = 0, 0
    
    if windows is not None:
        for k, (x, y, w, h) in windows.items():
            color = (0, 0, 0)
            if k == "xp_wheel":
                color = (0, 255, 255) # Yellow
            elif k == "text_buttons":
                color = (255, 255, 255) # White
            elif k == "icon_hp" or k == "target_icon_hp":
                color = (0, 255, 0) # Green
            elif k == "icon_end" or k == "target_icon_end":
                color = (255, 0, 0) # Blue
            elif "target_" in k:
                color = (255, 100, 0) # Orange for target anchors
            elif "team_" in k:
                color = (0, 200, 200) # Cyan for team anchors
                
            cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
            
            # Only include player bar components in the player window box calculation
            if not k.startswith("target_") and not k.startswith("team_") and k != "chat_top":
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x+w)
                max_y = max(max_y, y+h)
            
    if target_box:
        tx, ty, tw, th = target_box
        cv2.rectangle(img, (tx, ty), (tx+tw, ty+th), (0, 165, 255), 2)
        cv2.putText(img, f"Target: {target_type}", (tx, ty - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

        # Draw target bars if icons found
        if windows and "target_icon_hp" in windows:
            hx, hy, hw, hh = windows["target_icon_hp"]
            # Bar width is roughly 100-110 pixels in these crops.
            # We'll just draw a placeholder bar for now or use the right edge logic if we had it.
            cv2.rectangle(img, (hx+hw, hy), (hx+hw+100, hy+hh), (0, 255, 0), 1)
        if windows and "target_icon_end" in windows:
            ex, ey, ew, eh = windows["target_icon_end"]
            cv2.rectangle(img, (ex+ew, ey), (ex+ew+100, ey+eh), (255, 0, 0), 1)

    if windows and min_x < 99999: 
        # Drawing full player window
        px, py = max(0, min_x - 10), max(0, min_y - 10)
        pw, ph = (max_x - min_x) + 20, (max_y - min_y) + 40
        
        if "icon_hp" in windows and "xp_wheel" in windows:
            hx, hy, hw, hh = windows["icon_hp"]
            xx, xy, xw, xh = windows["xp_wheel"]
            bar_w = xx - (hx + hw)
            if bar_w > 0:
                cv2.rectangle(img, (hx+hw, hy), (hx+hw+bar_w, hy+hh), (0, 255, 0), 1)

        if "icon_end" in windows and "xp_wheel" in windows:
            ex, ey, ew, eh = windows["icon_end"]
            xx, xy, xw, xh = windows["xp_wheel"]
            bar_w = xx - (ex + ew)
            if bar_w > 0:
                cv2.rectangle(img, (ex+ew, ey), (ex+ew+bar_w, ey+eh), (255, 0, 0), 1)
        
        cv2.rectangle(img, (px, py), (px+pw, py+ph), (255, 0, 255), 3)

    t_team = time.perf_counter()
    
    out_path = os.path.join(out_dir, os.path.basename(shot_path))
    cv2.imwrite(out_path, img)
    print(f"  -> Saved to {out_path}", flush=True)
    
    if profile:
        t_save = time.perf_counter()
        print(f"  [Timing] Detect: {(t_detect - t_start)*1000:.1f}ms | Player: {(t_player - t_detect)*1000:.1f}ms | Target: {(t_target - t_player)*1000:.1f}ms | Team: {(t_team - t_target)*1000:.1f}ms | Save: {(t_save - t_team)*1000:.1f}ms")

def main():
    parser = argparse.ArgumentParser(description="Diagnostic tool for CoH Bot perception.")
    parser.add_argument("--file", help="Process a single screenshot file")
    parser.add_argument("--dir", default="tests/screenshots/full", help="Process a directory of screenshots")
    parser.add_argument("--out", default="tests/screenshots/full_annotated", help="Output directory")
    parser.add_argument("--profile", action="store_true", help="Print timing logs for processing bottleneck profiling")
    args = parser.parse_args()
    
    player_tpl_dir = 'tests/screenshots/references/player_bar'
    target_tpl_dir = 'tests/screenshots/references/target_anchors'
    
    team_tpl_dir = 'tests/screenshots/references/team'
    
    os.makedirs(args.out, exist_ok=True)
    
    # Load templates
    templates = {
        "xp_wheel": load_templates([f"{player_tpl_dir}/xp*.png"]),
        "text_buttons": load_templates([f"{player_tpl_dir}/text*.png"]),
        "icon_hp": load_templates([f"{player_tpl_dir}/ICON_hp_*.png"]),
        "icon_end": load_templates([f"{player_tpl_dir}/ICON_end_*.png"]),
        "target_actions": load_templates([f"{target_tpl_dir}/anchor_actions*.png"]),
        "target_corner": load_templates([f"{target_tpl_dir}/corner_tl*.png"]),
        "target_edge": load_templates([f"{target_tpl_dir}/anchor_edge_top.png"]),
        "target_none": load_templates([f"{target_tpl_dir}/text_no_target*.png"]),
        "target_archetype": load_templates([f"{target_tpl_dir}/icon_archetype_*.png"]),
        "target_icon_hp": load_templates([f"{target_tpl_dir}/target_icon_hp.png"]),
        "target_icon_end": load_templates([f"{target_tpl_dir}/target_icon_end.png"]),
        "team_top": load_templates([f"{team_tpl_dir}/window_top.png"]),
        "team_bottom": load_templates([f"{team_tpl_dir}/team_bar__*.png"]),
        "team_dock": load_templates([f"{team_tpl_dir}/dock_button.png"]),
        "team_close": load_templates([f"{team_tpl_dir}/close_button.png"]),
        "chat_top": load_templates([f"{team_tpl_dir}/chat_window_top.png"]),
        "bar_end": load_templates([f"{team_tpl_dir}/bar_end*.png"]),
        "member_hp": load_templates([f"tests/screenshots/references/team_anchors/member_hp_glimmer.png"]),
        "member_dead": load_templates([f"tests/screenshots/references/team_anchors/member_dead_glimmer.png"])
    }
    
    detector = TemplateWindowDetector(templates, threshold=0.7)
    
    if args.file:
        process_image(args.file, detector, args.out, profile=args.profile)
    else:
        pattern = os.path.join(args.dir, "*.png")
        files = glob.glob(pattern)
        if not files:
            print(f"No images found in {args.dir}")
            return
        for f in files:
            process_image(f, detector, args.out, profile=args.profile)

if __name__ == '__main__':
    main()
