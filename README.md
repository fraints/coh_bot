# City of Heroes Bot

A simple, extensible automation bot for City of Heroes.

## Architecture

```
coh_bot/
├── main.py                   # Entry point and main loop
├── config.py                 # Global configuration
├── requirements.txt
├── bot/
│   ├── perception/
│   │   └── screen_reader.py  # Screen capture and image analysis
│   ├── brain/
│   │   ├── fsm.py            # Finite State Machine engine
│   │   └── states.py         # Concrete game states
│   └── actions/
│       └── input_handler.py  # Keyboard/mouse input facade
└── tests/
    ├── test_fsm.py
    └── test_perception.py
```

## Modules

| Module | Responsibility |
|---|---|
| **Perception** | Captures screen regions and detects game state (health, targets, enemies) |
| **Brain (FSM)** | Transitions between states (Idle, Combat, Navigation) based on percepts |
| **Actions** | Sends key presses and clicks to the game window |

## Getting Started

```bash
pyenv activate coh

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

## Extensibility

- **New states:** Add a class to `bot/brain/states.py` inheriting `BaseState` and register it in `fsm.py`.
- **New perceptions:** Add detection methods to `bot/perception/screen_reader.py`.
- **New actions:** Add methods to `bot/actions/input_handler.py`.
- **Config tuning:** All tunable parameters live in `config.py`.

## Diagnostics

The `tools/snapshot_debug.py` script allows you to verify perception logic against static screenshots. It detects and annotates:
* **Player Bar**: XP wheel, HP/Endurance icons and bars (including fallback logic).
* **Target Window**: Localization (anchored by Actions button, Corner, or Edge) and Classification (Enemy, Player, NPC, None).
* **Team Window**: Counts members (Alive/Dead) and calculates precise geometric bounds for HP and Endurance bars using hybrid color-scanline detection.
* **Coordinate Output**: Precise (X, Y) and [WxH] data for every detected element is printed to the console.

### Usage

```bash
# Set up environment
export PYTHONPATH=$(pwd)
pyenv activate coh

# Process all standard screenshots
python tools/snapshot_debug.py --dir tests/screenshots/full --out tests/screenshots/full_annotated

# Process target-specific reference images
python tools/snapshot_debug.py --dir tests/screenshots/references/target --out tests/screenshots/references/target_annotated

# Process team-specific reference images
python tools/snapshot_debug.py --dir tests/screenshots/references/team --out tests/screenshots/references/team_annotated

# Process a single specific file
python tools/snapshot_debug.py --file tests/screenshots/full/team_both_dead.png --out ./debug_out
```

### Legend
- **Yellow Box**: XP Wheel
- **White Box**: Player Bar Text Buttons
- **Green Box**: Health Icon/Bar
- **Blue Box**: Endurance Icon/Bar
- **Orange Box**: Target Window Anchors (Actions, Corner, Edge)
- **Thick Magenta/Orange Outer Box**: Final estimated window boundaries.

### Troubleshooting
If new UI elements aren't being detected, you can regenerate or add new templates using:
```bash
python tools/create_target_templates.py
```
This script extracts anchors and icons from the reference images in `tests/screenshots/references/target/`.
