"""
main.py - Entry point for coh_bot.

Wires together Perception, Brain, and Action modules and runs the main loop.
"""

from __future__ import annotations

import logging
import signal
import sys
import time

import config
from bot.actions.input_handler import InputHandler
from bot.brain.fsm import FSM
from bot.brain.states import IdleState
from bot.perception.screen_reader import ScreenReader

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_context() -> dict:
    """Instantiate and return the shared context passed to all FSM states."""
    return {
        "reader": ScreenReader(),
        "input": InputHandler(),
    }


def main() -> None:
    logger.info("coh_bot starting up. Tick rate: %.2fs", config.TICK_RATE)

    context = build_context()
    fsm = FSM(initial_state=IdleState, context=context)

    # Allow Ctrl-C to exit cleanly
    running = True

    def _handle_sigint(sig, frame):
        nonlocal running
        logger.info("Interrupted – shutting down.")
        running = False

    signal.signal(signal.SIGINT, _handle_sigint)

    # ── Main loop ────────────────────────────────────────────────────────────
    while running:
        tick_start = time.monotonic()

        try:
            fsm.tick()
        except Exception:  # noqa: BLE001
            logger.exception("Unhandled exception in FSM tick – continuing.")

        elapsed = time.monotonic() - tick_start
        sleep_time = max(0.0, config.TICK_RATE - elapsed)
        time.sleep(sleep_time)

    logger.info("coh_bot stopped.")


if __name__ == "__main__":
    main()
