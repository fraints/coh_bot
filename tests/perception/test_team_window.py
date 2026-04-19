import pytest
import cv2
import os
import numpy as np
from bot.perception.window_detector import TemplateWindowDetector
from bot.perception.extractors.team_window import TeamWindowExtractor, TeamMemberLayout
from bot.models import TeamMember

# --- Configuration ---
REFERENCE_DIR = os.path.join("tests", "screenshots", "references")
SCREENSHOT_DIR = os.path.join("tests", "screenshots", "full")
TOLERANCE = 5  # pixels

# Expected values for each screenshot
# Format: (window_top_y, member_count, m1_y_alive_status)
# Note: window_top_y is the dock_button.y - 5
EXPECTATIONS = {
    "team1.jpeg": (505, 8, "Alive", 538),
    "team2.jpg": (234, 8, "Alive", 268),
    "team3.jpg": (111, 8, "Alive", 143),
    "team4.jpeg": (450, 3, "Alive", 484),
    "team_low_hp.png": (638, 2, "Alive", 673),
    "team_high_hp.png": (480, 2, "Alive", 514),
    "team_both_dead.png": (486, 2, "Dead", 520),
    "team_other_dead.png": (486, 2, "Dead", 520),
    "team_low_hp2.png": (480, 2, "Alive", 514),
}

def load_templates(paths: list[str]) -> list:
    import glob
    ret = []
    for p in paths:
        for f in glob.glob(p):
            t = cv2.imread(f)
            if t is not None:
                ret.append(t)
    return ret

@pytest.fixture(scope="module")
def detector():
    player_tpl_dir = os.path.join(REFERENCE_DIR, 'player_bar')
    target_tpl_dir = os.path.join(REFERENCE_DIR, 'target_anchors')
    team_tpl_dir = os.path.join(REFERENCE_DIR, 'team')
    
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
    return TemplateWindowDetector(templates, threshold=0.7)

@pytest.fixture(scope="module")
def extractor(detector):
    return TeamWindowExtractor(detector, REFERENCE_DIR)

@pytest.mark.parametrize("filename, expected_data", EXPECTATIONS.items())
def test_team_window_detection(filename, expected_data, extractor):
    exp_ty, exp_count, exp_status, exp_m1_y = expected_data
    
    img_path = os.path.join(SCREENSHOT_DIR, filename)
    img = cv2.imread(img_path)
    assert img is not None, f"Could not load image {img_path}"
    
    results = extractor.extract_team(img)
    
    # Check count
    assert len(results) == exp_count, f"Expected {exp_count} members in {filename}, found {len(results)}"
    
    # Check first member (Leader)
    member, layout = results[0]
    lx, ly, lw, lh = layout.hp_bar_box
    
    assert member.status == exp_status, f"Expected M1 status {exp_status} in {filename}, found {member.status}"
    assert abs(ly - exp_m1_y) <= TOLERANCE, f"M1 Y {ly} deviates more than {TOLERANCE}px from expected {exp_m1_y} in {filename}"
    
    # Check window anchoring consistency (infer ty from M1 if extractor doesn't return it)
    # Actually, the extractor logic is what we are testing.
    # ty is roughly ly - 34
    ty = ly - 34
    assert abs(ty - exp_ty) <= TOLERANCE, f"Inferred Window Top Y {ty} deviates from expected {exp_ty} in {filename}"
