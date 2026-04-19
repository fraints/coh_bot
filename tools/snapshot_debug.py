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
    ref_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "screenshots", "references")
    from bot.perception.extractors.team_window import TeamWindowExtractor
    team_extractor = TeamWindowExtractor(detector, ref_dir)
    team_results = team_extractor.extract_team(img)
    
    if team_results:
        # Drawing just for the first member to frame the window
        _, first_layout = team_results[0]
        tx, ty, _, _ = first_layout.hp_bar_box
        # We don't have the full window box anymore, but we can infer it or just draw members
        
        # Draw the members
        for member_idx, (member, layout) in enumerate(team_results, 1):
            lx, ly, lw, lh = layout.hp_bar_box
            ex, ey, ew, eh = layout.end_bar_box
            
            status = member.status
            
            # HP Bar
            cv2.rectangle(img, (lx, ly), (lx + lw, ly + lh), (0, 255, 0), 1) # HP Green
            cv2.putText(img, f"M{member_idx}: {status}", (lx, ly + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
            
            # END Bar
            cv2.rectangle(img, (lx, ey), (lx + lw, ey + eh), (255, 0, 0), 1) # Blue

            print(f"  [Team Member {member_idx}] {status} at ({lx}, {ly}) end_y={ey} bounds: {lw}w", flush=True)

  

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
    parser.add_argument("--file", nargs='+', help="Process one or more screenshot files")
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
        for f in args.file:
            process_image(f, detector, args.out, profile=args.profile)
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
