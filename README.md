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

## Troubleshooting and Verification

### Manual Verification
You can run the detection and extraction scripts on any screenshot to see the system's performance:

```bash
# Test window detection only
PYENV_VERSION=coh python tools/test_window_detection.py <path_to_screenshot>

# Test full data extraction (bars, OCR, etc.)
PYENV_VERSION=coh python tools/test_data_extraction.py <path_to_screenshot>
```

### Automated Testing
Automated tests verify that the system is resilient to different resolutions and UI layouts.

```bash
# Run all tests
PYENV_VERSION=coh pytest

# Run perception tests only (includes resolution-robustness checks)
PYENV_VERSION=coh pytest tests/test_perception_dynamic.py
```

> [!IMPORTANT]
> **Dependencies**: Automated testing requires `pytesseract` and a local installation of `Tesseract OCR`. On Linux, you can install it via `sudo apt install tesseract-ocr`.

## Extensibility

- **New states:** Add a class to `bot/brain/states.py` inheriting `BaseState` and register it in `fsm.py`.
- **New perceptions:** Add detection methods to `bot/perception/screen_reader.py`.
- **New actions:** Add methods to `bot/actions/input_handler.py`.
- **Config tuning:** All tunable parameters live in `config.py`.
