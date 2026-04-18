import cv2
import os

def create_target_templates():
    ref_dir = 'tests/screenshots/references'
    target_dir = os.path.join(ref_dir, 'target')
    tpl_dir = os.path.join(ref_dir, 'target_anchors')
    os.makedirs(tpl_dir, exist_ok=True)
    
    # 1. Actions button
    img_actions = cv2.imread(os.path.join(target_dir, 'target_enemy.png'))
    if img_actions is not None:
        # Actions is at the bottom.
        # Crop tighter on "Actions" to avoid as much background as possible.
        actions_tpl = img_actions[73:87, 15:85]
        if actions_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'anchor_actions.png'), actions_tpl)
            print("Saved anchor_actions.png")

    # 2. No Target text
    # The user provided text_no_target_corrected.png, we just need to make sure it's used.
    # We'll also keep a crop from the actual game if needed, but the user's one is best.

    # 3. Top-left corner (Fixed to be tighter to avoid background)
    if img_actions is not None:
        # Tighter 10x10 crop of the actual blue corner.
        tl_tpl = img_actions[0:12, 0:12]
        if tl_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'corner_tl.png'), tl_tpl)
            print("Saved corner_tl.png")
            
    # 4. Bubble Edge (horizontal top border)
    if img_actions is not None:
        edge_tpl = img_actions[0:5, 30:80]
        if edge_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'anchor_edge_top.png'), edge_tpl)
            print("Saved anchor_edge_top.png")

    # 5. Archetype icons
    img_player = cv2.imread(os.path.join(target_dir, 'target_player.png'))
    if img_player is not None:
        at_tpl = img_player[20:45, 180:215]
        if at_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'icon_archetype_red.png'), at_tpl)
            print("Saved icon_archetype_red.png")
            
    img_team = cv2.imread(os.path.join(target_dir, 'target_player_teammate.png'))
    if img_team is not None:
        at_tpl = img_team[20:45, 180:215]
        if at_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'icon_archetype_purple.png'), at_tpl)
            print("Saved icon_archetype_purple.png")

    # 6. Actions button (None version)
    img_none = cv2.imread(os.path.join(target_dir, 'target_no_target.png'))
    if img_none is not None:
        actions_tpl = img_none[73:87, 15:85]
        if actions_tpl.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'anchor_actions_none.png'), actions_tpl)
            print("Saved anchor_actions_none.png")

    # 7. Target Bar Icons
    if img_actions is not None:
        # HP bar left edge
        target_hp_icon = img_actions[41:51, 62:72]
        if target_hp_icon.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'target_icon_hp.png'), target_hp_icon)
            print("Saved target_icon_hp.png")
            
        # End bar left edge
        target_end_icon = img_actions[51:61, 62:72]
        if target_end_icon.size > 0:
            cv2.imwrite(os.path.join(tpl_dir, 'target_icon_end.png'), target_end_icon)
            print("Saved target_icon_end.png")

if __name__ == '__main__':
    create_target_templates()
