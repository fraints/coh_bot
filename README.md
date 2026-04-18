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

The `tools/snapshot_debug.py` script allows you to verify perception logic against static screenshots. It annotates detected UI elements (XP wheel, HP/End bars) with colored bounding boxes.

### Usage

```bash
# Process all screenshots in the default directory
export PYTHONPATH=$(pwd)
pyenv activate coh
python tools/snapshot_debug.py --dir tests/screenshots/full

# Process a single specific file
python tools/snapshot_debug.py --file tests/screenshots/full/team_both_dead.png
```

Annotated images are saved to `tests/screenshots/full_annotated/`. Console output will indicate the exact coordinates and size of detected elements, including whether any fallback logic (e.g., for the endurance bar) was triggered.
