import cv2
import os
import glob

def create_team_templates():
    team_dir = 'tests/screenshots/references/team'
    tpl_dir = 'tests/screenshots/references/team_anchors'
    os.makedirs(tpl_dir, exist_ok=True)

    # 1. HP bar glimmer (active) from team1.png
    img_team1 = cv2.imread(os.path.join(team_dir, 'team1.png'))
    if img_team1 is not None:
        # Include the left edge blue border
        hp_tpl = img_team1[114:132, 14:35]
        if hp_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'member_hp_glimmer.png'), hp_tpl)
            print("Saved member_hp_glimmer.png")

    # 2. HP bar edge (dead) from team4.png
    img_team4 = cv2.imread(os.path.join(team_dir, 'team4.png'))
    if img_team4 is not None:
        # Include the left edge blue border for dead members
        dead_tpl = img_team4[44:66, 14:35]
        if dead_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'member_dead_glimmer.png'), dead_tpl)
            print("Saved member_dead_glimmer.png")

if __name__ == '__main__':
    create_team_templates()
