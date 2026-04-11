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
# Create virtual environment
python -m venv venv
source venv/bin/activate

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
