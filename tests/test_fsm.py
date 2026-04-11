"""
test_fsm.py - Unit tests for the FSM engine and state transitions.
"""

from __future__ import annotations

from typing import Optional, Type
from unittest.mock import MagicMock

import pytest

from bot.brain.fsm import BaseState, FSM
from bot.brain.states import CombatState, IdleState, LowHealthState, ScanState
from bot.perception.screen_reader import GameState


# ── Stub states for FSM engine tests ─────────────────────────────────────────

class AlwaysTransitionState(BaseState):
    """Immediately transitions to TargetState."""
    target: Type[BaseState]

    def tick(self, fsm: FSM) -> Optional[Type[BaseState]]:
        return self.__class__.target


class NeverTransitionState(BaseState):
    def tick(self, fsm: FSM) -> Optional[Type[BaseState]]:
        return None


# ── FSM engine tests ──────────────────────────────────────────────────────────

class TestFSM:
    def test_starts_in_initial_state(self):
        fsm = FSM(initial_state=NeverTransitionState)
        assert isinstance(fsm.current_state, NeverTransitionState)

    def test_on_enter_called(self):
        calls = []

        class TrackingState(BaseState):
            def on_enter(self, fsm):
                calls.append("entered")

            def tick(self, fsm):
                return None

        fsm = FSM(initial_state=TrackingState)
        assert calls == ["entered"]

    def test_transition_changes_state(self):
        AlwaysTransitionState.target = NeverTransitionState
        fsm = FSM(initial_state=AlwaysTransitionState)
        fsm.tick()
        assert isinstance(fsm.current_state, NeverTransitionState)

    def test_on_exit_called_on_transition(self):
        exits = []

        class ExitTracker(BaseState):
            def on_exit(self, fsm):
                exits.append("exited")

            def tick(self, fsm):
                return NeverTransitionState

        fsm = FSM(initial_state=ExitTracker)
        fsm.tick()
        assert exits == ["exited"]

    def test_no_transition_when_tick_returns_none(self):
        fsm = FSM(initial_state=NeverTransitionState)
        for _ in range(5):
            fsm.tick()
        assert isinstance(fsm.current_state, NeverTransitionState)

    def test_context_is_shared(self):
        ctx = {"value": 42}
        fsm = FSM(initial_state=NeverTransitionState, context=ctx)
        assert fsm.context["value"] == 42


# ── State logic tests ─────────────────────────────────────────────────────────

def _make_fsm(state_cls: Type[BaseState], game_state: GameState) -> FSM:
    """Helper: build an FSM with a mocked reader and input."""
    reader = MagicMock()
    reader.capture.return_value = game_state
    inp = MagicMock()
    return FSM(
        initial_state=state_cls,
        context={"reader": reader, "input": inp},
    )


class TestIdleState:
    def test_stays_idle_immediately(self):
        fsm = _make_fsm(IdleState, GameState())
        fsm.tick()
        assert isinstance(fsm.current_state, IdleState)

    def test_transitions_to_scan_after_duration(self):
        import time
        fsm = _make_fsm(IdleState, GameState())
        # Simulate time passing by patching _entered_at
        fsm.current_state._entered_at = 0.0  # epoch → always past threshold
        fsm.tick()
        assert isinstance(fsm.current_state, ScanState)


class TestScanState:
    def test_transitions_to_combat_when_target_acquired(self):
        fsm = _make_fsm(ScanState, GameState(has_target=True))
        fsm.tick()
        assert isinstance(fsm.current_state, CombatState)

    def test_returns_to_idle_after_max_attempts(self):
        fsm = _make_fsm(ScanState, GameState(has_target=False))
        # Exhaust all attempts
        for _ in range(ScanState._MAX_TAB_ATTEMPTS + 1):
            fsm.tick()
            if not isinstance(fsm.current_state, ScanState):
                break
        assert isinstance(fsm.current_state, IdleState)


class TestCombatState:
    def test_transitions_to_scan_when_target_lost(self):
        fsm = _make_fsm(CombatState, GameState(has_target=False, player_hp_pct=1.0))
        fsm.tick()
        assert isinstance(fsm.current_state, ScanState)

    def test_transitions_to_low_health_when_hp_drops(self):
        import config
        fsm = _make_fsm(
            CombatState,
            GameState(has_target=True, player_hp_pct=config.HEALTH_LOW_THRESHOLD - 0.01),
        )
        fsm.tick()
        assert isinstance(fsm.current_state, LowHealthState)

    def test_stays_in_combat_when_healthy_with_target(self):
        fsm = _make_fsm(CombatState, GameState(has_target=True, player_hp_pct=1.0))
        # Set last attack far in the past so cooldown doesn't block
        fsm.current_state._last_attack = 0.0
        fsm.tick()
        assert isinstance(fsm.current_state, CombatState)


class TestLowHealthState:
    def test_stays_in_recovery_when_hp_still_low(self):
        import config
        fsm = _make_fsm(
            LowHealthState,
            GameState(player_hp_pct=config.HEALTH_LOW_THRESHOLD - 0.01),
        )
        fsm.tick()
        assert isinstance(fsm.current_state, LowHealthState)

    def test_transitions_to_scan_when_recovered(self):
        fsm = _make_fsm(LowHealthState, GameState(player_hp_pct=1.0))
        fsm.tick()
        assert isinstance(fsm.current_state, ScanState)
