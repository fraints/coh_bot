"""
config.py - Global configuration for coh_bot.
All tunable parameters live here for easy modification.
"""

# ─── Timing ───────────────────────────────────────────────────────────────────
# How often the main loop ticks (seconds). Lower = more responsive, higher CPU.
TICK_RATE: float = 0.25

# ─── Perception ───────────────────────────────────────────────────────────────
# Monitor index for the game window (0 = primary). Adjust for multi-monitor setups.
MONITOR_INDEX: int = 1

# Confidence threshold for template matching (OpenCV TM_CCOEFF_NORMED, 0.0-1.0).
TEMPLATE_MATCH_THRESHOLD: float = 0.80

# Screen region bounding boxes (left, top, width, height) for ROI capture.
# These should be calibrated to the actual game UI layout.
REGIONS = {
    "health_bar": (10, 50, 200, 20),        # Player HP bar area
    "target_name": (400, 30, 300, 25),       # Target name text area
    "target_health": (400, 55, 300, 20),     # Target HP bar area
    "chat_log": (0, 600, 500, 200),          # Chat log feed
    "enemy_nearby": (350, 100, 500, 400),    # Center of screen for enemy detection
}

# ─── Actions ──────────────────────────────────────────────────────────────────
# Key bindings (should match in-game keybinds)
KEYBINDS = {
    "target_nearest": "tab",
    "attack_power_1": "1",
    "attack_power_2": "2",
    "heal_self": "h",
    "rest": "r",
    "follow": "f",
}

# Delay between individual key presses (seconds)
KEY_PRESS_DELAY: float = 0.05

# ─── Combat ───────────────────────────────────────────────────────────────────
# player HP% below which the bot should stop attacking and rest/heal
HEALTH_LOW_THRESHOLD: float = 0.30

# Minimum time (seconds) to wait between using the same power
POWER_COOLDOWN: float = 1.0
