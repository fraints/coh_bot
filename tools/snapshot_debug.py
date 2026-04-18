import cv2
import glob
import os
import argparse
import logging
from bot.perception.window_detector import TemplateWindowDetector

def load_templates(paths: list[str]) -> list:
    ret = []
    for p in paths:
        for f in glob.glob(p):
            t = cv2.imread(f)
            if t is not None:
                ret.append(t)
    return ret

def process_image(shot_path: str, detector: TemplateWindowDetector, out_dir: str):
    img = cv2.imread(shot_path)
    if img is None:
        print(f"Error: Could not read image {shot_path}")
        return

    print(f"\nProcessing {os.path.basename(shot_path)}", flush=True)
    detector.cached_boxes.clear()
    windows = detector.detect(img)
    
    # Validation & Fallback logic
    icon_hp = windows.get("icon_hp")
    icon_end = windows.get("icon_end")
    
    if icon_hp:
        hx, hy, hw, hh = icon_hp
        print(f"  [icon_hp] found at ({hx}, {hy}) [{hw}x{hh}]", flush=True)
        
        # Validate icon_end if it exists
        if icon_end:
            ex, ey, ew, eh = icon_end
            if abs(hx - ex) > 20 or ey < hy:
                print(f"  [icon_end] Rejected at ({ex}, {ey}): spatially inconsistent with HP bar", flush=True)
                icon_end = None
                del windows["icon_end"]
            else:
                print(f"  [icon_end] found at ({ex}, {ey}) [{ew}x{eh}]", flush=True)

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
    
    if "xp_wheel" in windows:
        x, y, w, h = windows["xp_wheel"]
        print(f"  [xp_wheel] found at ({x}, {y}) [{w}x{h}]", flush=True)
    if "text_buttons" in windows:
        x, y, w, h = windows["text_buttons"]
        print(f"  [text_buttons] found at ({x}, {y}) [{w}x{h}]", flush=True)

    # Annotation
    min_x, min_y = 99999, 99999
    max_x, max_y = 0, 0
    
    for k, (x, y, w, h) in windows.items():
        color = (0, 0, 0)
        if k == "xp_wheel":
            color = (0, 255, 255) # Yellow
        elif k == "text_buttons":
            color = (255, 255, 255) # White
        elif k == "icon_hp":
            color = (0, 255, 0) # Green
        elif k == "icon_end":
            color = (255, 0, 0) # Blue
            
        cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x+w)
        max_y = max(max_y, y+h)
        
    if windows:
        # Drawing full window and bars
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

    out_path = os.path.join(out_dir, os.path.basename(shot_path))
    cv2.imwrite(out_path, img)
    print(f"  -> Saved to {out_path}", flush=True)

def main():
    parser = argparse.ArgumentParser(description="Diagnostic tool for CoH Bot perception.")
    parser.add_argument("--file", help="Process a single screenshot file")
    parser.add_argument("--dir", default="tests/screenshots/full", help="Process a directory of screenshots")
    parser.add_argument("--out", default="tests/screenshots/full_annotated", help="Output directory")
    args = parser.parse_args()
    
    templates_dir = 'tests/screenshots/references/player_bar'
    
    os.makedirs(args.out, exist_ok=True)
    
    # Load templates
    templates = {
        "xp_wheel": load_templates([f"{templates_dir}/xp*.png"]),
        "text_buttons": load_templates([f"{templates_dir}/text*.png"]),
        "icon_hp": load_templates([f"{templates_dir}/ICON_hp_*.png"]),
        "icon_end": load_templates([f"{templates_dir}/ICON_end_*.png"])
    }
    
    detector = TemplateWindowDetector(templates, threshold=0.75)
    
    if args.file:
        process_image(args.file, detector, args.out)
    else:
        pattern = os.path.join(args.dir, "*.png")
        files = glob.glob(pattern)
        if not files:
            print(f"No images found in {args.dir}")
            return
        for f in files:
            process_image(f, detector, args.out)

if __name__ == '__main__':
    main()
