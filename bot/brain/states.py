"""
states.py - Concrete game states for coh_bot.

Each state encapsulates a self-contained behaviour.  Add new states here and
register them by returning the new class from an appropriate ``tick`` method.

State flow (initial):

    IdleState ──► ScanState ──► CombatState ──► LowHealthState
        ▲              │                              │
        └──────────────┴──────────────────────────────┘
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Type, TYPE_CHECKING

import config
from bot.brain.fsm import BaseState, FSM
from bot.perception.screen_reader import GameState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reader(fsm: FSM):
    """Shortcut to retrieve the ScreenReader from FSM context."""
    return fsm.context["reader"]


def _input(fsm: FSM):
    """Shortcut to retrieve the InputHandler from FSM context."""
    return fsm.context["input"]


def _perceive(fsm: FSM) -> GameState:
    """Capture and return a fresh GameState."""
    return _reader(fsm).capture()


# ── States ────────────────────────────────────────────────────────────────────

class IdleState(BaseState):
    """
    Default resting state.

    Waits briefly then transitions to ScanState to look for enemies.
    """
    _IDLE_DURATION = 1.0  # seconds to rest before scanning

    def on_enter(self, fsm: FSM) -> None:
        self._entered_at = time.monotonic()

    def tick(self, fsm: FSM) -> Optional[Type[BaseState]]:
        if time.monotonic() - self._entered_at >= self._IDLE_DURATION:
            return ScanState
        return None


class ScanState(BaseState):
    """
    Scan for a nearby enemy and attempt to acquire a target.

    Sends Tab to cycle to the nearest enemy.  If a target is detected,
    transition to CombatState; if we've cycled too many times without
    finding one, go back to IdleState.
    """
    _MAX_TAB_ATTEMPTS = 5

    def on_enter(self, fsm: FSM) -> None:
        self._attempts = 0

    def tick(self, fsm: FSM) -> Optional[Type[BaseState]]:
        state = _perceive(fsm)

        if state.has_target:
            logger.info("Target acquired – entering combat.")
            return CombatState

        if self._attempts >= self._MAX_TAB_ATTEMPTS:
            logger.info("No enemy found after %d attempts – returning to idle.", self._attempts)
            return IdleState

        _input(fsm).press_keybind("target_nearest")
        self._attempts += 1
        return None


class CombatState(BaseState):
    """
    Engage the current target with the configured power rotation.

    Power rotation is simple: alternate power slot 1 and 2 with a
    configurable cooldown between each.

    Transitions:
    * No target → ScanState (target died or de-selected)
    * Low HP     → LowHealthState
    """
    _POWER_SEQUENCE = ["attack_power_1", "attack_power_2"]

    def on_enter(self, fsm: FSM) -> None:
        self._power_index = 0
        self._last_attack = 0.0
        logger.info("Combat state entered.")

    def tick(self, fsm: FSM) -> Optional[Type[BaseState]]:
        state = _perceive(fsm)

        if state.player_hp_pct < config.HEALTH_LOW_THRESHOLD:
            return LowHealthState

        if not state.has_target:
            logger.info("Target lost – returning to scan.")
            return ScanState

        now = time.monotonic()
        if now - self._last_attack >= config.POWER_COOLDOWN:
            action = self._POWER_SEQUENCE[self._power_index % len(self._POWER_SEQUENCE)]
            _input(fsm).press_keybind(action)
            self._last_attack = now
            self._power_index += 1

        return None


class LowHealthState(BaseState):
    """
    Stop combat and attempt to recover HP (rest / heal).

    Transitions back to ScanState once HP is at an acceptable level.
    """
    _RECOVER_THRESHOLD = config.HEALTH_LOW_THRESHOLD + 0.20  # must recover 20% above the danger threshold

    def on_enter(self, fsm: FSM) -> None:
        logger.warning("Low health! HP below %.0f%% – entering recovery.", config.HEALTH_LOW_THRESHOLD * 100)
        _input(fsm).press_keybind("rest")

    def tick(self, fsm: FSM) -> Optional[Type[BaseState]]:
        state = _perceive(fsm)
        if state.player_hp_pct >= self._RECOVER_THRESHOLD:
            logger.info("HP recovered (%.0f%%) – returning to scan.", state.player_hp_pct * 100)
            return ScanState
        # Optionally try a heal power each tick
        _input(fsm).press_keybind("heal_self")
        return None
