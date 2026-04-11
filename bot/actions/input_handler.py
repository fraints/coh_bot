"""
input_handler.py - Action module for coh_bot.

Provides a thin, testable facade over pynput for sending keyboard and
mouse events to the game window.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from pynput.keyboard import Controller, Key, KeyCode

import config

logger = logging.getLogger(__name__)

# Map friendly names to pynput Key or KeyCode objects
_SPECIAL_KEYS: dict[str, Key] = {
    "tab": Key.tab,
    "space": Key.space,
    "enter": Key.enter,
    "esc": Key.esc,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
}


class InputHandler:
    """
    Sends keyboard and mouse inputs to whatever window currently has focus.

    Usage
    -----
    handler = InputHandler()
    handler.press_key("tab")    # target nearest enemy
    handler.press_key("1")      # fire power slot 1
    handler.press_keybind("target_nearest")   # resolve via config

    Notes
    -----
    * pynput works with most Linux X11/Wayland display servers.
    * For headless or Wayland-strict environments you may need to switch
      to the ``evdev`` backend (see README).
    """

    def __init__(self) -> None:
        self._keyboard = Controller()
        logger.info("InputHandler initialised.")

    # ── Public API ────────────────────────────────────────────────────────────

    def press_key(self, key: str, delay: Optional[float] = None) -> None:
        """
        Press and release a single key.

        Parameters
        ----------
        key:
            Either a single character (``"1"``, ``"h"``) or a special-key
            name as defined in ``_SPECIAL_KEYS`` (``"tab"``, ``"esc"``).
        delay:
            Override the default inter-key delay (``config.KEY_PRESS_DELAY``).
        """
        pynput_key = self._resolve_key(key)
        self._keyboard.press(pynput_key)
        time.sleep(delay if delay is not None else config.KEY_PRESS_DELAY)
        self._keyboard.release(pynput_key)
        logger.debug("Pressed key: %s", key)

    def press_keybind(self, action: str) -> None:
        """
        Press the key bound to *action* as configured in ``config.KEYBINDS``.

        Parameters
        ----------
        action:
            A key from ``config.KEYBINDS`` (e.g. ``"target_nearest"``).
        """
        key = config.KEYBINDS.get(action)
        if key is None:
            logger.warning("No keybind configured for action '%s'.", action)
            return
        self.press_key(key)

    def chord(self, *keys: str) -> None:
        """Press a combination of keys simultaneously (e.g. Ctrl+A)."""
        pynput_keys = [self._resolve_key(k) for k in keys]
        for k in pynput_keys:
            self._keyboard.press(k)
        time.sleep(config.KEY_PRESS_DELAY)
        for k in reversed(pynput_keys):
            self._keyboard.release(k)
        logger.debug("Chord: %s", keys)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_key(key: str):
        """Convert a string key name to a pynput ``Key`` or ``KeyCode``."""
        if key in _SPECIAL_KEYS:
            return _SPECIAL_KEYS[key]
        if len(key) == 1:
            return KeyCode.from_char(key)
        raise ValueError(f"Unknown key: '{key}'. Add it to _SPECIAL_KEYS if needed.")
